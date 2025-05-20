import sys
import os
import shutil
import urllib.parse
import threading
import locale
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from PyQt5.QtGui import QIcon, QBrush, QColor, QFont, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QTreeWidget, QTreeWidgetItem, QSplitter, QMessageBox, QDialog, QComboBox, QHeaderView, QFileDialog
)
from flask_cors import CORS
import browser_cookie3
import webbrowser
import time
import subprocess

ICON_PATHS = {
    "folder": "folder.png",
    "archive": "archive.png",
    "document": "document.png",
    "music": "music.png",
    "program": "program.png",
    "video": "video.png"
}
CATEGORY_TREE = [
    ("All",        "Tất cả",        "folder"),
    ("Compressed", "Tệp nén",       "archive"),
    ("Documents",  "Tài liệu",      "document"),
    ("Music",      "Âm nhạc",       "music"),
    ("Programs",   "Chương trình",  "program"),
    ("Video",      "Video",         "video"),
]

DOWNLOAD_ROOT = r"C:\Users\CHANHDIEN\Downloads"
COOKIES_FILE = r"D:\NhuanTinIDM\cookies.txt"

CATEGORY_FOLDERS = {
    'Video': os.path.join(DOWNLOAD_ROOT, "Video"),
    'Music': os.path.join(DOWNLOAD_ROOT, "Music"),
    'Documents': os.path.join(DOWNLOAD_ROOT, "Documents"),
    'Programs': os.path.join(DOWNLOAD_ROOT, "Programs"),
    'Compressed': os.path.join(DOWNLOAD_ROOT, "Compressed"),
    'Other': DOWNLOAD_ROOT
}
CATEGORIES = {
    'Video': ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.3gp', '.m4v', '.mpeg', '.mpg', '.wmv', '.asf', '.ogv', '.rm', '.rmvb', '.qt'],
    'Music': ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.aif', '.ra', '.wma'],
    'Documents': ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.ppt', '.pps', '.tif', '.tiff', '.plj'],
    'Programs': ['.exe', '.msi', '.apk', '.iso', '.img', '.bin', '.msu'],
    'Compressed': ['.zip', '.rar', '.7z', '.tar.gz', '.gz', '.bz2', '.gzip', '.tar', '.z', '.ace', '.arj', '.lzh', '.sit', '.sitx', '.sea']
}
CATEGORY_LABELS = {
    "Compressed": {"vi": "Tệp nén", "en": "Compressed"},
    "Documents": {"vi": "Tài liệu", "en": "Documents"},
    "Music": {"vi": "Âm nhạc", "en": "Music"},
    "Programs": {"vi": "Chương trình", "en": "Programs"},
    "Video": {"vi": "Video", "en": "Video"},
    "Other": {"vi": "Khác", "en": "Other"},
    "All": {"vi": "Tất cả", "en": "All"}
}

# Ngôn ngữ tự động
try:
    lang_tuple = locale.getlocale()
    LANG = lang_tuple[0] if lang_tuple and lang_tuple[0] else 'en'
except:
    LANG = 'en'
CURRENT_LANG = "vi" if LANG.lower().startswith("vi") else "en"

def get_category(filename):
    ext = os.path.splitext(filename)[1].lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return 'Other'

def get_save_path(filename, category=None):
    cat = category if category else get_category(filename if '%' not in filename else '.mp3')
    folder = CATEGORY_FOLDERS.get(cat, DOWNLOAD_ROOT)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, filename)

def format_seconds(secs):
    if secs <= 0 or secs > 365*24*3600:
        return "-"
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    elif m > 0:
        return f"{m}m {s:02d}s"
    else:
        return f"{s}s"

def is_youtube_or_social(url):
    return any(s in url for s in ['youtube.com', 'youtu.be', 'facebook.com', 'fb.watch', 'tiktok.com'])

# =============== FLASK SERVER ===============
# Chia sẻ biến manager giữa Flask và GUI
manager_instance = None

def run_api_server():
    global manager_instance
    app = Flask(__name__)
    CORS(app)

    @app.route('/add-link', methods=['POST'])
    def add_link():
        data = request.get_json()
        url = data.get('url')
        ftype = data.get('type', 'auto')
        format_id = data.get('format_id', None)
        target_ext = data.get('target_ext', None)
        bitrate = data.get('bitrate', '192')
        subtitle_lang = data.get('lang', None)
        print(f"Nhận link: {url} - Loại: {ftype} - Định dạng: {format_id}")
        if manager_instance:
            # Nếu type là auto hoặc không xác định, phân loại theo đuôi file
            if ftype == "auto" or not ftype:
                # Lấy đuôi file từ url
                path = urllib.parse.urlparse(url).path
                ext = os.path.splitext(path)[1].lower()
                cat = get_category("file" + ext)
                manager_instance.add_download_from_api(
                    url, cat, None, None, "192", None
                )
            else:
                manager_instance.add_download_from_api(
                    url, ftype, format_id, target_ext, bitrate, subtitle_lang
                )
        return jsonify({'status': 'ok'}), 200

    @app.route("/formats")
    def get_formats():
        url = request.args.get("url")
        if not hasattr(app, '_formats_cache'):
            app._formats_cache = {}
        if not hasattr(app, '_formats_threads'):
            app._formats_threads = {}
        cache = app._formats_cache
        threads = app._formats_threads
        # Nếu đã có cache, trả về ngay
        if url in cache:
            return jsonify(cache[url])
        # Nếu chưa có thread lấy formats, khởi động thread
        if url not in threads:
            def fetch_formats():
                ydl_opts = {"cookiefile": COOKIES_FILE, "quiet": True}
                video, audio, video_only = [], [], []
                try:
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        for f in info.get("formats", []):
                            # VIDEO+Audio
                            if f.get("vcodec") != "none" and f.get("acodec") != "none":
                                label = ""
                                if f.get("format_note"):
                                    label += f"{f['format_note']} "
                                if f.get("height"):
                                    label += f"{f['height']}p"
                                if f.get("fps"):
                                    label += f" {int(f['fps'])}fps"
                                label += f" .{f['ext']}"
                                video.append({
                                    "format_id": f["format_id"],
                                    "label": label.strip(),
                                    "ext": f['ext'],
                                    "filesize": round(f.get('filesize', 0)/1024/1024, 1) if f.get('filesize') else "?"
                                })
                            # VIDEO ONLY
                            elif f.get("vcodec") != "none" and f.get("acodec") == "none":
                                label = ""
                                if f.get("format_note"):
                                    label += f"{f['format_note']} "
                                if f.get("height"):
                                    label += f"{f['height']}p"
                                if f.get("fps"):
                                    label += f" {int(f['fps'])}fps"
                                label += f" (chỉ hình) .{f['ext']}"
                                video_only.append({
                                    "format_id": f["format_id"],
                                    "label": label.strip(),
                                    "ext": f['ext'],
                                    "filesize": round(f.get('filesize', 0)/1024/1024, 1) if f.get('filesize') else "?"
                                })
                            # AUDIO ONLY
                            elif f.get("vcodec") == "none" and f.get("acodec") != "none":
                                if f.get('ext') == 'mp4' or not f.get('format_id'):
                                    continue
                                label = ""
                                if f.get("abr"):
                                    label += f"{int(f['abr'])}kbps"
                                elif f.get("asr"):
                                    label += f"{int(f['asr'])}Hz"
                                else:
                                    label += "Audio"
                                if f.get("ext") == "m4a":
                                    label += " (AAC .m4a)"
                                elif f.get("ext") == "webm":
                                    label += " (Opus .webm)"
                                else:
                                    label += f" .{f['ext']}"
                                audio.append({
                                    "format_id": f["format_id"],
                                    "label": label.strip(),
                                    "ext": f['ext'],
                                    "filesize": round(f.get('filesize', 0)/1024/1024, 1) if f.get('filesize') else "?"
                                })
                    cache[url] = {"video": video, "video_only": video_only, "audio": audio}
                except Exception as e:
                    cache[url] = {"video": [], "video_only": [], "audio": [], "error": str(e)}
                # Xóa thread sau khi xong
                if url in threads:
                    del threads[url]
            t = threading.Thread(target=fetch_formats)
            t.daemon = True
            t.start()
            threads[url] = t
        # Nếu chưa có cache, trả về pending
        return jsonify({"status": "pending"})

    @app.route("/download", methods=["POST"])
    def download():
        data = request.json
        url = data["url"]
        typ = data["type"]
        format_id = data.get("format_id")
        outtmpl = os.path.join(DOWNLOAD_ROOT, "%(title)s.%(ext)s")
        ydl_opts = {
            "cookiefile": COOKIES_FILE,
            "outtmpl": outtmpl,
            "concurrent_fragment_downloads": 16,
            "retries": 5,
            "force_overwrite": True,
            "continuedl": True,
            "quiet": True,
            "noprogress": False,
            "merge_output_format": "mp4",
        }
        if typ == "video" and format_id:
            ydl_opts["format"] = f"{format_id}+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        elif typ == "audio" and format_id:
            ydl_opts["format"] = format_id
            target_ext = data.get("target_ext", "mp3")
            bitrate = data.get("bitrate", "192")
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": target_ext,
                "preferredquality": bitrate
            }]
        elif typ == "subtitle":
            ydl_opts.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [data["lang"]],
                "skip_download": True
            })
        else:
            return jsonify({"status": "error"}), 400

        def bg():
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                print(f"DOWNLOAD ERROR: {e}")
        threading.Thread(target=bg, daemon=True).start()
        return jsonify({"status": "ok"})

    @app.route('/upload-cookies', methods=['POST'])
    def upload_cookies():
        cookies_txt = request.data.decode('utf-8')
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(cookies_txt)
        print(f"[INFO] Đã nhận cookies từ extension và ghi vào {COOKIES_FILE}")
        return jsonify({'status': 'ok'})

    app.run(port=5678)

# ============= PYQT5 GUI ================
class AudioOptionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tùy chọn tải âm thanh")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Chọn bitrate xuất (kbps):"))
        self.bitrate_box = QComboBox()
        self.bitrate_box.addItems(["32", "64", "128", "192", "256", "320"])
        layout.addWidget(self.bitrate_box)
        layout.addWidget(QLabel("Chọn định dạng lưu:"))
        self.fmt_box = QComboBox()
        self.fmt_box.addItems(["mp3", "m4a", "ogg"])
        layout.addWidget(self.fmt_box)
        self.select_btn = QPushButton("Chọn")
        self.select_btn.clicked.connect(self.accept)
        layout.addWidget(self.select_btn)
        self.setLayout(layout)
    def get_selection(self):
        return self.bitrate_box.currentText(), self.fmt_box.currentText()

class VideoOptionDialog(QDialog):
    def __init__(self, video_list, video_only_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn định dạng video tải")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Chọn chất lượng video muốn tải:"))
        self.listwidget = QComboBox()
        self.options = []
        # Nhóm Video có tiếng: gồm cả video+audio và video only (đánh dấu để tự động ghép audio nếu cần)
        self.listwidget.addItem("--- Video có tiếng ---")
        self.options.append({"type": "header"})
        # Thêm video+audio trước, chỉ add nếu filesize khác '?'
        if video_list:
            for item in video_list:
                if item.get('filesize', '?') == '?':
                    continue
                label = f"{item.get('label','')} [{item.get('ext','')}], size={item.get('filesize','?')}MB (có tiếng)"
                self.listwidget.addItem(label)
                self.options.append({"type": "video_audio", "item": item})
        # Thêm video only (sẽ ghép audio), chỉ add nếu filesize khác '?'
        if video_only_list:
            for item in video_only_list:
                if item.get('filesize', '?') == '?':
                    continue
                label = f"{item.get('label','')} [{item.get('ext','')}], size={item.get('filesize','?')}MB (ghép tiếng)"
                self.listwidget.addItem(label)
                self.options.append({"type": "video_only_merge", "item": item})
        # Nhóm Video không tiếng: chỉ video only
        self.listwidget.addItem("--- Video không tiếng ---")
        self.options.append({"type": "header"})
        if video_only_list:
            for item in video_only_list:
                if item.get('filesize', '?') == '?':
                    continue
                label = f"{item.get('label','')} [{item.get('ext','')}], size={item.get('filesize','?')}MB (không tiếng)"
                self.listwidget.addItem(label)
                self.options.append({"type": "video_only", "item": item})
        layout.addWidget(self.listwidget)
        self.select_btn = QPushButton("Chọn")
        self.select_btn.clicked.connect(self.accept)
        layout.addWidget(self.select_btn)
        self.setLayout(layout)
    def get_selection(self):
        idx = self.listwidget.currentIndex()
        # Không cho chọn tiêu đề nhóm
        if idx < 0 or idx >= len(self.options) or self.options[idx]["type"] == "header":
            QMessageBox.warning(self, "Chưa chọn", "Bạn phải chọn một định dạng video!")
            return None
        return self.options[idx]

class FormatFetcher(QThread):
    result = pyqtSignal(dict)
    error = pyqtSignal(str)
    def __init__(self, url):
        super().__init__()
        self.url = url
    def run(self):
        try:
            resp = requests.get(f"http://127.0.0.1:5678/formats?url={self.url}", timeout=30)
            self.result.emit(resp.json())
        except Exception as e:
            self.error.emit(str(e))

class DownloadThread(QThread):
    progress = pyqtSignal(str, str, float, str, str, str, str)
    finished = pyqtSignal(str)
    def __init__(self, url, filename, format_id=None, is_audio=False, audio_ext=None, bitrate="192"):
        super().__init__()
        self.url = url
        self.filename = filename  # chỉ là %(title)s (không có đuôi)
        self.format_id = format_id
        self.is_audio = is_audio
        self.audio_ext = audio_ext
        self.bitrate = bitrate

    def run(self):
        try:
            if is_youtube_or_social(self.url):
                # Bước 1: tải file gốc về thư mục Video
                video_outtmpl = self.save_path_override if hasattr(self, 'save_path_override') else get_save_path(f"{self.filename}.%(ext)s", category="Video")
                ydl_opts = {
                    'outtmpl': video_outtmpl,
                    'progress_hooks': [self.ytdlp_hook],
                    'noplaylist': True,
                    'concurrent_fragment_downloads': 16,
                    'retries': 5,
                    'force_overwrite': True,
                    'continuedl': True,
                    'cookiefile': COOKIES_FILE,
                    'quiet': True,
                    'noprogress': False,
                    'merge_output_format': 'mp4',
                }
                if self.format_id:
                    ydl_opts['format'] = self.format_id
                if self.format_id and '+' in str(self.format_id) and not self.is_audio:
                    ydl_opts['postprocessors'] = [
                        {
                            'key': 'FFmpegVideoRemuxer',
                            'preferedformat': 'mp4',
                        }
                    ]
                if self.is_audio and self.audio_ext:
                    ydl_opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": self.audio_ext,
                        "preferredquality": self.bitrate,
                    }]
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.url])
                # Kiểm tra file video sau khi tải xong (chỉ áp dụng cho video)
                if not self.is_audio:
                    video_folder = CATEGORY_FOLDERS['Video']
                    video_exts = ['.mp4', '.webm', '.mkv', '.avi']
                    video_file = None
                    max_mtime = 0
                    for f in os.listdir(video_folder):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in video_exts:
                            fpath = os.path.join(video_folder, f)
                            mtime = os.path.getmtime(fpath)
                            if mtime > max_mtime:
                                max_mtime = mtime
                                video_file = f
                    if video_file:
                        video_path = os.path.join(video_folder, video_file)
                        size_mb = os.path.getsize(video_path) / 1024 / 1024
                        print(f"[INFO] File {video_file} đã tải xong, dung lượng {size_mb:.2f}MB.")
                    # Không cảnh báo nếu không có file mp4, chỉ cảnh báo nếu không có file video nào
            else:
                # Tải file thường (Google Drive, OneDrive, Fshare, ...), không dùng yt-dlp
                self.download_direct_file(self.url, self.filename, self.save_path_override if hasattr(self, 'save_path_override') else None)
                self.finished.emit(self.filename)
        except Exception as e:
            import traceback
            print("[ERROR] DownloadThread exception:", e)
            traceback.print_exc()
            self.progress.emit("ERROR", "-", 0, f"Lỗi: {e}", "-", "-", "-")
            self.finished.emit("ERROR")

    def download_direct_file(self, url, filename, save_path_override=None):
        local_path = save_path_override if save_path_override else get_save_path(filename)
        # Nếu filename không có đuôi, lấy đuôi từ url
        if not os.path.splitext(local_path)[1]:
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1]
            if ext:
                local_path += ext
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get('Content-Length', 0))
                downloaded = 0
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = (downloaded/total*100) if total else 0
                            size_str = f"{round(total/1024/1024,2)} MB" if total else "-"
                            speed_str = "-"
                            time_left = "-"
                            cat = get_category(local_path)
                            cat_label = CATEGORY_LABELS[cat][CURRENT_LANG] if cat in CATEGORY_LABELS else ""
                            status_str = f"{percent:.0f}%"
                            self.progress.emit(
                                os.path.basename(local_path), size_str, percent, status_str, time_left, speed_str, cat_label
                            )
        except Exception as e:
            raise e

    def ytdlp_hook(self, d):
        if d['status'] == 'downloading':
            info = d.get('info_dict') or {}
            filename = d.get('filename')
            title = info.get('title', '')
            ext = info.get('ext', 'mp4')
            if title:
                filename_show = f"{title}.{ext}"
            elif filename:
                filename_show = os.path.basename(filename)
            else:
                filename_show = "downloading"
            if filename_show.endswith('.mp3'):
                filename_show = filename_show[:-4]
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded/total*100) if total else 0
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            size_str = f"{round(total/1024/1024,2)} MB" if total else "-"
            speed_str = f"{round(speed/1024,2)} KB/s" if speed else "-"
            time_left = format_seconds(eta) if eta else "-"
            cat = get_category(filename_show)
            cat_label = CATEGORY_LABELS[cat][CURRENT_LANG] if cat in CATEGORY_LABELS else ""
            status_str = f"{percent:.0f}%"
            self.progress.emit(
                filename_show, size_str, percent, status_str, time_left, speed_str, cat_label
            )
        elif d['status'] == 'finished':
            info = d.get('info_dict') or {}
            filename = d.get('filename')
            title = info.get('title', '')
            ext = info.get('ext', 'mp4')
            if title:
                filename_show = f"{title}.{ext}"
            elif filename:
                filename_show = os.path.basename(filename)
            else:
                filename_show = "finished"
            if filename_show.endswith('.mp3.mp3'):
                filename_show = filename_show[:-4]
            size_str = "-"
            cat = get_category(filename_show)
            cat_label = CATEGORY_LABELS[cat][CURRENT_LANG] if cat in CATEGORY_LABELS else ""
            self.progress.emit(
                filename_show, size_str, 100, "Hoàn thành", "-", "-", cat_label
            )
            self.finished.emit(filename_show)

def get_icon_path_by_ext(ext):
    ext = ext.lower()
    archive_exts = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.gzip', '.tar.gz', '.z', '.ace', '.arj', '.lzh', '.sit', '.sitx', '.sea']
    document_exts = ['.pdf', '.docx', '.doc', '.xlsx', '.pptx', '.txt', '.ppt', '.pps', '.tif', '.tiff', '.plj']
    music_exts = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.aif', '.ra', '.wma']
    program_exts = ['.exe', '.msi', '.apk', '.iso', '.img', '.bin', '.msu']
    video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.3gp', '.m4v', '.mpeg', '.mpg', '.wmv', '.asf', '.ogv', '.rm', '.rmvb', '.qt']
    if ext in archive_exts:
        return os.path.join('D:/NhuanTinIDM/desktop', 'archive.png')
    if ext in document_exts:
        return os.path.join('D:/NhuanTinIDM/desktop', 'document.png')
    if ext in music_exts:
        return os.path.join('D:/NhuanTinIDM/desktop', 'music.png')
    if ext in program_exts:
        return os.path.join('D:/NhuanTinIDM/desktop', 'program.png')
    if ext in video_exts:
        return os.path.join('D:/NhuanTinIDM/desktop', 'video.png')
    return os.path.join('D:/NhuanTinIDM/desktop', 'folder.png')

def get_icon_path_by_type(file_type):
    type_map = {
        'video': 'video.png',
        'audio': 'music.png',
        'music': 'music.png',
        'document': 'document.png',
        'documents': 'document.png',
        'program': 'program.png',
        'programs': 'program.png',
        'compressed': 'archive.png',
        'archive': 'archive.png',
        'other': 'folder.png'
    }
    return os.path.join('D:/NhuanTinIDM/desktop', type_map.get(str(file_type).lower(), 'folder.png'))

class DownloadDialog(QDialog):
    def __init__(self, url, default_category, default_path, file_type_hint=None, parent=None):
        super().__init__(parent)
        self.file_type_hint = file_type_hint
        self.setWindowTitle("Download File Info")
        self.setWindowIcon(QIcon('D:/NhuanTinIDM/desktop/app.png'))
        self.url = url
        self.selected_path = default_path
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setFixedWidth(800)
        layout = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()
        # Icon file (căn giữa dọc)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        right.addStretch(1)
        right.addWidget(self.icon_label, alignment=Qt.AlignHCenter)
        # Dung lượng
        self.size_label = QLabel("-")
        right.addWidget(self.size_label, alignment=Qt.AlignHCenter)
        right.addStretch(1)
        # URL
        left.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit(url)
        self.url_edit.setReadOnly(True)
        left.addWidget(self.url_edit)
        # Category
        left.addWidget(QLabel("Category:"))
        cat_hbox = QHBoxLayout()
        self.category_box = QComboBox()
        self.category_box.addItems(["Programs", "Video", "Music", "Documents", "Compressed", "Other"])
        self.category_box.setCurrentText(default_category)
        cat_hbox.addWidget(self.category_box)
        self.add_cat_btn = QPushButton("+")
        self.add_cat_btn.setFixedWidth(24)
        cat_hbox.addWidget(self.add_cat_btn)
        left.addLayout(cat_hbox)
        # Save As
        left.addWidget(QLabel("Save As:"))
        save_hbox = QHBoxLayout()
        self.path_edit = QLineEdit(default_path)
        save_hbox.addWidget(self.path_edit)
        browse_btn = QPushButton("...")
        browse_btn.clicked.connect(self.browse)
        save_hbox.addWidget(browse_btn)
        left.addLayout(save_hbox)
        # Description
        left.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        left.addWidget(self.desc_edit)
        # Buttons
        btn_hbox = QHBoxLayout()
        self.later_btn = QPushButton("Download Later")
        self.start_btn = QPushButton("Start Download")
        self.cancel_btn = QPushButton("Cancel")
        btn_hbox.addWidget(self.later_btn)
        btn_hbox.addWidget(self.start_btn)
        btn_hbox.addWidget(self.cancel_btn)
        left.addLayout(btn_hbox)
        layout.addLayout(left, 4)
        layout.addLayout(right, 1)
        self.setLayout(layout)
        self.later_btn.clicked.connect(self.download_later)
        self.start_btn.clicked.connect(self.start_download)
        self.cancel_btn.clicked.connect(self.reject)
        self.path_edit.textChanged.connect(self.update_icon_and_size)
        self.category_box.currentTextChanged.connect(self.suggest_save_path_by_category)
        self.user_edited_path = False
        self.path_edit.textEdited.connect(self.set_user_edited_path)
        # Popup hiện ngay, icon/size cập nhật sau
        QTimer.singleShot(100, self.update_icon_and_size)
        # Tự động đổi đuôi file nếu là mp4 hoặc webm (nếu chưa user edit)
        if self.file_type_hint in ["video", "mp4", "webm"] and not self.user_edited_path:
            ext = ".mp4" if self.file_type_hint in ["video", "mp4"] else ".webm"
            base_name = os.path.splitext(os.path.basename(default_path))[0]
            while '.' in base_name:
                base_name = os.path.splitext(base_name)[0]
            new_path = os.path.join(os.path.dirname(default_path), base_name + ext)
            self.path_edit.setText(new_path)
    def browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save As", self.path_edit.text())
        if path:
            self.path_edit.setText(path)
    def download_later(self):
        self.done(2)
    def start_download(self):
        self.done(1)
    def set_user_edited_path(self):
        self.user_edited_path = True
    def update_icon_and_size(self):
        fname = self.path_edit.text()
        ext = os.path.splitext(fname)[1].lower()
        if ext:
            icon_path = get_icon_path_by_ext(ext)
        elif self.file_type_hint:
            icon_path = get_icon_path_by_type(self.file_type_hint)
            if not os.path.exists(icon_path):
                cat = self.category_box.currentText().lower()
                icon_path = get_icon_path_by_type(cat)
            if not os.path.exists(icon_path):
                icon_path = get_icon_path_by_ext('')
        else:
            cat = self.category_box.currentText().lower()
            icon_path = get_icon_path_by_type(cat)
            if not os.path.exists(icon_path):
                icon_path = get_icon_path_by_ext('')
        if os.path.exists(icon_path):
            self.icon_label.setPixmap(QPixmap(icon_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.icon_label.setPixmap(QPixmap(get_icon_path_by_ext('')).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # Lấy dung lượng file
        size = self.get_file_size(self.url)
        self.size_label.setText(size)
    def suggest_save_path_by_category(self):
        if not self.user_edited_path:
            fname = os.path.basename(self.path_edit.text())
            cat = self.category_box.currentText()
            suggested = get_save_path(fname, category=cat)
            self.path_edit.setText(suggested)
        # Cập nhật icon khi đổi category
        self.update_icon_and_size()
    def get_file_size(self, url):
        try:
            if is_youtube_or_social(url):
                ydl_opts = {"cookiefile": COOKIES_FILE, "quiet": True}
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    filesize = info.get('filesize') or info.get('filesize_approx')
                    if filesize:
                        return f"{round(filesize/1024/1024,2)} MB"
            else:
                resp = requests.head(url, allow_redirects=True, timeout=5)
                size = resp.headers.get('Content-Length')
                if size:
                    return f"{round(int(size)/1024/1024,2)} MB"
        except Exception as e:
            pass
        return "-"

class DownloadManager(QMainWindow):
    add_download_signal = pyqtSignal(str, str, object, object, object, object)
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("app.png"))
        self.setWindowTitle("IDM Pikachu")
        self.resize(1200, 600)
        # Tree category Việt hóa & đa ngôn ngữ
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels([CATEGORY_LABELS["All"][CURRENT_LANG]])
        self.category_tree.clear()  # Xóa hết các node cũ (nếu cần)

        # Thêm các node chính
        all_item = QTreeWidgetItem(["Tất cả"])
        self.category_tree.addTopLevelItem(all_item)
        # Loại bỏ hai node Video và Âm thanh top-level
        # video_item = QTreeWidgetItem(["Video"])
        # audio_item = QTreeWidgetItem(["Âm thanh"])
        # self.category_tree.addTopLevelItem(video_item)
        # self.category_tree.addTopLevelItem(audio_item)

        # Thêm node "By Nhuận Tín" dưới cùng
        by_nt_item = QTreeWidgetItem(["© By Nhuận Tín"])
        by_nt_item.setForeground(0, QBrush(QColor("#2176b8")))
        by_nt_item.setFont(0, QFont("Arial", weight=QFont.Bold))
        self.category_tree.addTopLevelItem(by_nt_item)
        self.category_items = {"All": all_item}
        for cat in ["Compressed", "Documents", "Music", "Programs", "Video"]:
            item = QTreeWidgetItem([CATEGORY_LABELS[cat][CURRENT_LANG]])
            icon_key = {
                "Compressed": "archive",
                "Documents": "document",
                "Music": "music",
                "Programs": "program",
                "Video": "video"
            }.get(cat, "folder")
            icon_path = ICON_PATHS.get(icon_key)
            if icon_path and os.path.exists(icon_path):
                item.setIcon(0, QIcon(icon_path))
            all_item.addChild(item)
            self.category_items[cat] = item
        all_item.setExpanded(True)
        self.category_tree.itemClicked.connect(self.on_category_selected)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Tên tệp", "Kích thước", "Trạng thái", "Thời gian còn lại", "Tốc độ", "Phân loại"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Các cột co giãn đều khi thay đổi kích thước cửa sổ
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.link_label = QLabel("Liên kết tải:")
        self.link_input = QLineEdit()
        self.add_btn = QPushButton("Thêm liên kết")
        self.add_btn.clicked.connect(self.handle_add_link)
        self.pause_btn = QPushButton("Tạm dừng")
        self.pause_btn.clicked.connect(self.handle_pause)
        self.resume_btn = QPushButton("Tiếp tục")
        self.resume_btn.clicked.connect(self.handle_resume)
        self.clear_btn = QPushButton("Xóa")
        self.clear_btn.clicked.connect(self.clear_selected)
        self.clear_all_btn = QPushButton("Xóa tất cả")
        self.clear_all_btn.clicked.connect(self.clear_all)
        self.option_video_btn = QPushButton("Tùy chọn Video")
        self.option_video_btn.clicked.connect(self.optimized_show_video_options)
        self.option_audio_btn = QPushButton("Tùy chọn Audio")
        self.option_audio_btn.clicked.connect(self.optimized_show_audio_options)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.resume_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.clear_all_btn)
        input_row = QHBoxLayout()
        input_row.addWidget(self.link_label)
        input_row.addWidget(self.link_input)
        input_row.addWidget(self.option_video_btn)
        input_row.addWidget(self.option_audio_btn)
        top_layout = QHBoxLayout()
        right_layout = QVBoxLayout()
        right_layout.addLayout(top_layout)
        right_layout.addLayout(input_row)
        right_layout.addLayout(btn_row)
        right_layout.addWidget(self.table)
        left_widget = QWidget()
        left_vbox = QVBoxLayout()
        left_vbox.setContentsMargins(0,0,0,0)
        left_vbox.setSpacing(0)
        left_vbox.addWidget(self.category_tree)
        left_widget.setLayout(left_vbox)
    
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([140, 400])
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        container = QWidget()
        c_layout = QHBoxLayout()
        c_layout.setContentsMargins(0,0,0,0)
        c_layout.setSpacing(0)
        c_layout.addWidget(splitter)
        container.setLayout(c_layout)
        self.setCentralWidget(container)
        self.selected_video_format = None
        self.selected_audio_format = None
        self.selected_bitrate = "192"
        self.downloads = []
        self.add_download_signal.connect(self._add_download_from_api_gui)

    def on_category_selected(self, item, col):
        # Xác định cat_key (Compressed, Documents, ...)
        cat_key = None
        for key, label_map in CATEGORY_LABELS.items():
            if label_map[CURRENT_LANG] == item.text(0):
                cat_key = key
                break
        files = []
        if cat_key is None or cat_key == "All":
            for cat, folder in CATEGORY_FOLDERS.items():
                files += self._get_files_for_category(cat)
        else:
            files = self._get_files_for_category(cat_key)
        self._update_table(files)

    def _get_files_for_category(self, cat_key):
        folder = CATEGORY_FOLDERS.get(cat_key)
        if not folder or not os.path.exists(folder):
            return []
        filters = CATEGORIES.get(cat_key, [])
        file_list = []
        for name in os.listdir(folder):
            ext = os.path.splitext(name)[1].lower()
            if ext in filters:
                file_list.append(os.path.join(folder, name))
        return file_list

    def _update_table(self, files):
        self.table.setRowCount(0)
        for f in files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(f)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{os.path.getsize(f)//1024} KB"))
            self.table.setItem(row, 2, QTableWidgetItem(""))
            self.table.setItem(row, 3, QTableWidgetItem(""))
            self.table.setItem(row, 4, QTableWidgetItem(""))
            cat = get_category(f)
            cat_label = CATEGORY_LABELS[cat][CURRENT_LANG] if cat in CATEGORY_LABELS else ""
            self.table.setItem(row, 5, QTableWidgetItem(cat_label))

    def optimized_show_audio_options(self):
        url = self.link_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập liên kết trước!")
            return
        self.audio_fetcher = FormatFetcher(url)
        self.audio_fetcher.result.connect(self._show_audio_options_dialog)
        self.audio_fetcher.error.connect(lambda msg: QMessageBox.critical(self, "Lỗi", msg))
        self.audio_fetcher.start()

    def _show_audio_options_dialog(self, data):
        dialog = AudioOptionDialog(self)
        if dialog.exec_():
            bitrate, target_ext = dialog.get_selection()
            audio_list = data.get("audio", [])
            audio_item = None
            bitrate_int = int(bitrate)
            min_diff = float('inf')
            for item in audio_list:
                try:
                    item_abr = int(item.get('label', '').split('kbps')[0].strip())
                    diff = abs(item_abr - bitrate_int)
                    if diff < min_diff:
                        min_diff = diff
                        audio_item = item
                except:
                    continue
            if audio_item:
                self.selected_audio_format = (audio_item, target_ext, bitrate)
                self.selected_video_format = None
                self.handle_add_link()
            else:
                QMessageBox.warning(self, "Không tìm thấy", "Không tìm được bitrate gần nhất!")

    def optimized_show_video_options(self):
        url = self.link_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập liên kết trước!")
            return
        self.video_fetcher = FormatFetcher(url)
        self.video_fetcher.result.connect(self._show_video_options_dialog)
        self.video_fetcher.error.connect(lambda msg: QMessageBox.critical(self, "Lỗi", msg))
        self.video_fetcher.start()

    def _show_video_options_dialog(self, data):
        dialog = VideoOptionDialog(data.get("video", []), data.get("video_only", []), self)
        if dialog.exec_():
            selection = dialog.get_selection()
            if not selection:
                return
            if selection["type"] == "video_audio":
                # Video+audio có sẵn
                self.selected_video_format = selection["item"]
                self.selected_audio_format = None
                self.handle_add_link()
            elif selection["type"] == "video_only_merge":
                # Video only, tự động ghép audio only tốt nhất (ưu tiên m4a)
                item = selection["item"]
                audio_list = data.get("audio", [])
                best_audio = None
                best_abr = 0
                # Ưu tiên audio ext là m4a (AAC)
                for a in audio_list:
                    if a.get('ext', '').lower() == 'm4a':
                        try:
                            abr = int(a.get('label', '').split('kbps')[0].strip())
                            if abr > best_abr:
                                best_abr = abr
                                best_audio = a
                        except:
                            continue
                # Nếu không có m4a, lấy audio ext khác (ví dụ opus)
                if not best_audio:
                    for a in audio_list:
                        try:
                            abr = int(a.get('label', '').split('kbps')[0].strip())
                            if abr > best_abr:
                                best_abr = abr
                                best_audio = a
                        except:
                            continue
                if best_audio:
                    format_id = f"{item['format_id']}+{best_audio['format_id']}"
                    merged_item = item.copy()
                    merged_item['format_id'] = format_id
                    self.selected_video_format = merged_item
                    self.selected_audio_format = None
                    self.handle_add_link()
                else:
                    QMessageBox.warning(self, "Không tìm thấy audio", "Không tìm được audio only phù hợp để ghép với video!")
            elif selection["type"] == "video_only":
                # Chỉ tải video only, không ghép audio
                self.selected_video_format = selection["item"]
                self.selected_audio_format = None
                self.handle_add_link()

    def handle_add_link(self):
        url = self.link_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Lỗi", "Bạn chưa nhập liên kết!")
            return

        filename = "%(title)s"
        format_id = None
        is_audio = False
        audio_ext = None
        bitrate = "192"

        if self.selected_audio_format:
            item, target_ext, bitrate = self.selected_audio_format
            format_id = item["format_id"]
            is_audio = True
            audio_ext = target_ext
        elif self.selected_video_format:
            item = self.selected_video_format
            format_id = item["format_id"]

        thread = DownloadThread(
            url,
            filename,
            format_id,
            is_audio,
            audio_ext,
            bitrate
        )
        row = self.table.rowCount()
        self.table.insertRow(row)
        cat_label = CATEGORY_LABELS["Music"][CURRENT_LANG] if is_audio else CATEGORY_LABELS["Video"][CURRENT_LANG]
        self.table.setItem(row, 0, QTableWidgetItem("Đang tải..."))
        self.table.setItem(row, 1, QTableWidgetItem("-"))
        self.table.setItem(row, 2, QTableWidgetItem("0%"))
        self.table.setItem(row, 3, QTableWidgetItem("-"))
        self.table.setItem(row, 4, QTableWidgetItem("-"))
        self.table.setItem(row, 5, QTableWidgetItem(cat_label))
        self.downloads.append((thread, row))
        thread.progress.connect(lambda *info, row=row: self.update_row(row, *info))
        thread.finished.connect(lambda fname: self.finish_row(fname))
        thread.start()
        self.link_input.clear()

    def update_row(self, row, filename, size, percent, status, time_left, speed, cat_label):
        # Cập nhật đúng các cột theo ý nghĩa
        self.table.setItem(row, 0, QTableWidgetItem(filename))  # Tên tệp
        self.table.setItem(row, 1, QTableWidgetItem(size))      # Kích thước
        # Trạng thái: chỉ thêm % nếu chưa có
        if isinstance(status, str) and status.endswith('%'):
            status_text = status
        elif isinstance(status, str) and status.replace('%','').isdigit():
            status_text = f"{status}%"
        elif status == 'Hoàn thành':
            status_text = "Hoàn thành"
        else:
            status_text = status
        self.table.setItem(row, 2, QTableWidgetItem(status_text))  # Trạng thái
        self.table.setItem(row, 3, QTableWidgetItem(time_left))    # Thời gian còn lại
        self.table.setItem(row, 4, QTableWidgetItem(speed))        # Tốc độ
        self.table.setItem(row, 5, QTableWidgetItem(cat_label))    # Phân loại

    def finish_row(self, filename):
        pass

    def handle_pause(self):
        for idx in self.table.selectionModel().selectedRows():
            row = idx.row()
            for t, r in self.downloads:
                if r == row:
                    t.terminate()
    def handle_resume(self):
        for idx in self.table.selectionModel().selectedRows():
            row = idx.row()
            for t, r in self.downloads:
                if r == row and not t.isRunning():
                    thread = DownloadThread(t.url, t.save_path, t.format_id, t.is_audio, t.audio_ext, t.bitrate)
                    self.downloads.append((thread, row))
                    thread.progress.connect(lambda *info, row=row: self.update_row(row, *info))
                    thread.finished.connect(lambda fname: self.finish_row(fname))
                    thread.start()
    def clear_selected(self):
        selected = sorted([idx.row() for idx in self.table.selectionModel().selectedRows()], reverse=True)
        for row in selected:
            for t, r in self.downloads:
                if r == row:
                    t.terminate()
            self.table.removeRow(row)
    def clear_all(self):
        for t, r in self.downloads:
            t.terminate()
        self.table.setRowCount(0)

    # ======= Thêm hàm này để nhận link từ API và bắt đầu download =======
    def add_download_from_api(self, url, ftype, format_id=None, target_ext=None, bitrate="192", subtitle_lang=None):
        # Phát signal để main thread xử lý
        self.add_download_signal.emit(url, ftype, format_id, target_ext, bitrate, subtitle_lang)

    def _add_download_from_api_gui(self, url, ftype, format_id=None, target_ext=None, bitrate="192", subtitle_lang=None):
        # Nếu là link YouTube/Facebook/TikTok thì lấy tiêu đề video
        def get_video_title_and_ext(url):
            try:
                ydl_opts = {"cookiefile": COOKIES_FILE, "quiet": True}
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get("title", "downloaded_file")
                    ext = info.get("ext", "mp4")
                    return title, ext
            except Exception as e:
                return None, None
        is_social = is_youtube_or_social(url)
        if is_social:
            title, ext = get_video_title_and_ext(url)
            if not title:
                title = "downloaded_file"
            if not ext:
                ext = ".mp4"
            # Loại bỏ mọi đuôi cũ khỏi title trước khi thêm ext
            base_title = title
            while '.' in base_title:
                base_title = os.path.splitext(base_title)[0]
            fname = f"{base_title}.{ext}" if not base_title.endswith(f".{ext}") else base_title
            # Nếu là audio, set cat = "Music"
            if ftype == "audio":
                cat = "Music"
            else:
                cat = "Video"
        else:
            path = urllib.parse.urlparse(url).path
            fname = os.path.basename(path)
            ext = os.path.splitext(fname)[1].lower()
            cat = get_category("file" + ext)
            if not fname:
                fname = "downloaded_file"
        save_path = get_save_path(fname, category=cat)
        # Nếu là audio và có target_ext, đổi đuôi file Save As thành .mp3 (hoặc target_ext)
        if ftype == "audio" and target_ext:
            base_name = os.path.splitext(os.path.basename(save_path))[0]
            while '.' in base_name:
                base_name = os.path.splitext(base_name)[0]
            save_path = os.path.join(os.path.dirname(save_path), base_name + '.' + target_ext)
        file_type_hint = ftype if ftype else cat.lower()
        dialog = DownloadDialog(url, cat, save_path, file_type_hint=file_type_hint)
        dialog.raise_()
        dialog.activateWindow()
        result = dialog.exec_()
        if result == 1:  # Start Download
            save_path = dialog.path_edit.text()
            cat = dialog.category_box.currentText()
            # Nếu là audio, loại bỏ mọi đuôi cũ, chỉ giữ tên gốc (không thêm .mp3), để yt-dlp tự thêm đuôi
            if ftype == "audio" and target_ext:
                base_name = os.path.splitext(os.path.basename(save_path))[0]
                while '.' in base_name:
                    base_name = os.path.splitext(base_name)[0]
                save_path_no_ext = os.path.join(os.path.dirname(save_path), base_name)
                thread = DownloadThread(
                    url, base_name, format_id, True, target_ext, bitrate
                )
                thread.save_path_override = save_path_no_ext
            else:
                base_name = os.path.splitext(os.path.basename(save_path))[0]
                while '.' in base_name:
                    base_name = os.path.splitext(base_name)[0]
                thread = DownloadThread(
                    url, base_name, format_id, ftype=="audio", target_ext, bitrate
                )
                thread.save_path_override = save_path
            row = self.table.rowCount()
            self.table.insertRow(row)
            cat_label = CATEGORY_LABELS.get(cat, {CURRENT_LANG: cat}).get(CURRENT_LANG, cat)
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(save_path)))
            self.table.setItem(row, 1, QTableWidgetItem("-"))
            self.table.setItem(row, 2, QTableWidgetItem("0%"))
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.table.setItem(row, 4, QTableWidgetItem("-"))
            self.table.setItem(row, 5, QTableWidgetItem(cat_label))
            self.downloads.append((thread, row))
            thread.progress.connect(lambda *info, row=row: self.update_row(row, *info))
            thread.finished.connect(lambda fname: self.finish_row(fname))
            thread.start()
        elif result == 2:
            QMessageBox.information(self, "Download Later", "Đã lưu vào danh sách chờ (chưa tải ngay). Tính năng này cần bổ sung thêm nếu muốn quản lý danh sách chờ.")

def export_youtube_cookies_to_txt(output_file):
    try:
        import pythoncom
        pythoncom.CoInitialize()
        import browser_cookie3
        cj = browser_cookie3.chrome(domain_name='youtube.com')
        with open(output_file, 'w', encoding='utf-8') as f:
            for c in cj:
                f.write(
                    f"{c.domain}\t"
                    f"{'TRUE' if c.domain_specified else 'FALSE'}\t"
                    f"{c.path}\t"
                    f"{'TRUE' if c.secure else 'FALSE'}\t"
                    f"{int(c.expires) if c.expires else 0}\t"
                    f"{c.name}\t"
                    f"{c.value}\n"
                )
        print(f"[INFO] Đã tự động lấy cookies YouTube từ Chrome vào {output_file}")
    except Exception as e:
        print(f"[WARNING] Không lấy được cookies từ Chrome: {e}")

def is_cookies_expired(cookies_file):
    try:
        with open(cookies_file, 'r', encoding='utf-8') as f:
            now = int(time.time())
            for line in f:
                if line.strip().startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) < 7:
                    continue
                expires = int(parts[4])
                if expires == 0 or expires > now:
                    return False  # Có ít nhất 1 cookie còn hạn
        return True  # Tất cả cookies đều hết hạn
    except Exception as e:
        print(f"[WARNING] Không kiểm tra được cookies: {e}")
        return True  # Nếu lỗi thì coi như hết hạn

def request_extension_update_cookies():
    print("[INFO] Yêu cầu extension gửi cookies mới...")
    webbrowser.open_new_tab('https://www.youtube.com/?getcookies=1')

if __name__ == "__main__":
    threading.Thread(target=export_youtube_cookies_to_txt, args=(COOKIES_FILE,), daemon=True).start()
    threading.Thread(target=run_api_server, daemon=True).start()
    app = QApplication(sys.argv)
    win = DownloadManager()
    manager_instance = win  # <-- Gán biến này để Flask gọi được hàm download
    win.show()
    sys.exit(app.exec_())
