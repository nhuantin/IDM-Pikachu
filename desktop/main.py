import sys
import os
import shutil
import urllib.parse
import threading
import locale
import requests
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QTreeWidget, QTreeWidgetItem, QSplitter, QMessageBox, QDialog, QComboBox
)

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
    'Video': ['.mp4', '.mkv', '.avi', '.mov', '.webm'],
    'Music': ['.mp3', '.wav', '.flac', '.ogg', '.m4a'],
    'Documents': ['.pdf', '.docx', '.xlsx', '.pptx', '.txt'],
    'Programs': ['.exe', '.msi'],
    'Compressed': ['.zip', '.rar', '.7z', '.tar.gz']
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
def run_api_server():
    app = Flask(__name__)

    @app.route("/formats")
    def get_formats():
        url = request.args.get("url")
        ydl_opts = {"cookiefile": COOKIES_FILE, "quiet": True}
        video, audio, video_only = [], [], []
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
        return jsonify({"video": video, "video_only": video_only, "audio": audio})

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
    app.run(port=5678)

threading.Thread(target=run_api_server, daemon=True).start()

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
        if video_list:
            for item in video_list:
                label = f"{item.get('label','')} [{item.get('ext','')}], size={item.get('filesize','?')}MB"
                self.listwidget.addItem(label)
                self.options.append(item)
        if video_only_list:
            for item in video_only_list:
                label = f"{item.get('label','')} [{item.get('ext','')}], size={item.get('filesize','?')}MB"
                self.listwidget.addItem(label)
                self.options.append(item)
        layout.addWidget(self.listwidget)
        self.select_btn = QPushButton("Chọn")
        self.select_btn.clicked.connect(self.accept)
        layout.addWidget(self.select_btn)
        self.setLayout(layout)
    def get_selection(self):
        idx = self.listwidget.currentIndex()
        if idx < 0 or idx >= len(self.options):
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
            resp = requests.get(f"http://127.0.0.1:5678/formats?url={self.url}", timeout=8)
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
            # Bước 1: tải file gốc về thư mục Video
            video_outtmpl = get_save_path(f"{self.filename}.%(ext)s", category="Video")
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
            if self.is_audio and self.audio_ext:
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.audio_ext,
                    "preferredquality": self.bitrate,
                }]
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            # Bước 2: Move file mp3 (sau khi convert) sang thư mục Music
            video_folder = CATEGORY_FOLDERS['Video']
            music_folder = CATEGORY_FOLDERS['Music']
            # Tìm file mp3 mới nhất trong Video (cùng tên với title)
            mp3_file = None
            for f in os.listdir(video_folder):
                if f.endswith('.mp3'):
                    mp3_file = f
                    break
            if mp3_file:
                src = os.path.join(video_folder, mp3_file)
                dst = os.path.join(music_folder, mp3_file)
                if not os.path.exists(music_folder):
                    os.makedirs(music_folder, exist_ok=True)
                shutil.move(src, dst)
                self.finished.emit(dst)
            else:
                self.finished.emit("")

        except Exception as e:
            self.progress.emit("ERROR", "-", 0, f"Lỗi: {e}", "-", "-", "-")
            self.finished.emit("ERROR")

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

class DownloadManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDM Pikachu")
        try: self.setWindowIcon(QIcon("app.png"))
        except: pass
        self.resize(1200, 600)
        # Tree category Việt hóa & đa ngôn ngữ
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels([CATEGORY_LABELS["All"][CURRENT_LANG]])
        all_item = QTreeWidgetItem([CATEGORY_LABELS["All"][CURRENT_LANG]])
        icon_path = ICON_PATHS.get("folder")
        if icon_path and os.path.exists(icon_path):
            all_item.setIcon(0, QIcon(icon_path))
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
        self.category_tree.addTopLevelItem(all_item)
        all_item.setExpanded(True)
        self.category_tree.itemClicked.connect(self.on_category_selected)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Tên tệp", "Kích thước", "Trạng thái", "Thời gian còn lại", "Tốc độ", "Phân loại"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
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
        right_layout = QVBoxLayout()
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
            item = dialog.get_selection()
            if item:
                self.selected_video_format = item
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
        self.table.setItem(row, 0, QTableWidgetItem(filename))
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
        if status == 'Hoàn thành':
            status_text = "Hoàn thành"
        else:
            status_text = status
        self.table.setItem(row, 0, QTableWidgetItem(filename))
        self.table.setItem(row, 1, QTableWidgetItem(size))
        self.table.setItem(row, 2, QTableWidgetItem(status_text))
        self.table.setItem(row, 3, QTableWidgetItem(time_left))
        self.table.setItem(row, 4, QTableWidgetItem(speed))
        self.table.setItem(row, 5, QTableWidgetItem(cat_label))

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DownloadManager()
    win.show()
    sys.exit(app.exec_())
