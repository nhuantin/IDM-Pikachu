import sys
import os
import urllib.parse
import time
import socket
import threading
import locale
import requests
import subprocess 
import sys, urllib.parse
from PyQt5.QtCore import pyqtSignal
from yt_dlp import YoutubeDL
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QTreeWidget, QTreeWidgetItem, QSplitter, QMessageBox
)

class DownloadThread(QThread):
    ...
    def run(self):
        ...
        fast_download(self.url, save_path)

LANGUAGES = {
    'vi': {
        'add_url': 'Thêm liên kết',
        'pause': 'Tạm dừng',
        'resume': 'Tiếp tục',
        'delete': 'Xóa',
        'download_link': 'Liên kết tải:',
        'downloading': 'Đang tải...',
        'completed': 'Hoàn thành',
        'all_downloads': 'Tất cả',
        'status': 'Trạng thái',
        'filename': 'Tên tệp',
        'size': 'Kích thước',
        'time_left': 'Thời gian còn lại',
        'transfer_rate': 'Tốc độ',
        'category': 'Video',
    },
    'en': {
        'add_url': 'Add URL',
        'pause': 'Pause',
        'resume': 'Resume',
        'delete': 'Delete',
        'download_link': 'Download link:',
        'downloading': 'Downloading...',
        'completed': 'Completed',
        'all_downloads': 'All Downloads',
        'status': 'Status',
        'filename': 'File Name',
        'size': 'Size',
        'time_left': 'Time left',
        'transfer_rate': 'Transfer rate',
        'category': 'Category',
    }
}

lang_code = (locale.getlocale()[0] or 'vi').split('_')[0].lower()
if lang_code not in LANGUAGES:
    lang_code = 'vi'
L = LANGUAGES[lang_code]

CATEGORY_LABELS = {
    'Video': L['category'] if lang_code == 'vi' else 'Video',
    'Music': 'Nhạc' if lang_code == 'vi' else 'Music',
    'Documents': 'Tài liệu' if lang_code == 'vi' else 'Documents',
    'Programs': 'Chương trình' if lang_code == 'vi' else 'Programs',
    'Compressed': 'Nén' if lang_code == 'vi' else 'Compressed'
}

CATEGORIES = {
    'Video': ['.mp4', '.mkv', '.avi', '.mov'],
    'Music': ['.mp3', '.wav', '.flac'],
    'Documents': ['.pdf', '.docx', '.xlsx', '.pptx', '.txt'],
    'Programs': ['.exe', '.msi', '.zip', '.rar', '.tar.gz'],
    'Compressed': ['.zip', '.rar', '.7z', '.tar.gz']
}

DOWNLOAD_ROOT = r"C:\Users\CHANHDIEN\Downloads"

main_window = None

def fast_download(url, output):
    subprocess.run(['aria2c', '-x', '16', '-s', '16', '-o', output, url])

def extract_real_link(protocol_link):
    if protocol_link.startswith("idmapp://download?url=") or protocol_link.startswith("idmapp://download/?url="):
        qs = urllib.parse.urlparse(protocol_link).query
        link_real = urllib.parse.parse_qs(qs).get('url', [''])[0]
        link_real = urllib.parse.unquote(link_real)
        return link_real
    return protocol_link

def process_link(link):
    global main_window
    real_link = extract_real_link(link)
    print("Nhận link:", real_link)
    if main_window is not None:
        main_window.add_link_signal.emit(real_link)

def server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 5678))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        data = conn.recv(4096).decode()
        if data:
            process_link(data)
        conn.close()

def send_to_running_app(link):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5678))
        s.sendall(link.encode())
        s.close()
        return True
    except:
        return False

def main():
    global main_window
    if len(sys.argv) > 1:
        url = sys.argv[1]
        if send_to_running_app(url):
            sys.exit(0)
        else:
            threading.Thread(target=server, daemon=True).start()
            app = QApplication(sys.argv)
            win = DownloadManager()
            main_window = win
            win.show()
            process_link(url)
            sys.exit(app.exec_())
    else:
        threading.Thread(target=server, daemon=True).start()
        app = QApplication(sys.argv)
        win = DownloadManager()
        main_window = win
        win.show()
        sys.exit(app.exec_())

def get_category(filename):
    ext = os.path.splitext(filename)[1].lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return None

def get_save_path(filename):
    cat = get_category(filename)
    if cat:
        folder = os.path.join(DOWNLOAD_ROOT, CATEGORY_LABELS[cat])
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)
    return os.path.join(DOWNLOAD_ROOT, filename)

def format_seconds(secs):
    if secs <= 0 or secs > 365*24*3600:
        return "-"
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h} hour(s) {m:02d} min {s:02d} sec"
    elif m > 0:
        return f"{m} min {s:02d} sec"
    else:
        return f"{s} sec"

def get_filename_from_response(url, resp):
    cd = resp.headers.get("content-disposition")
    if cd:
        import re
        fname = re.findall('filename="?([^"]+)"?', cd)
        if fname:
            return fname[0]
    filename = os.path.basename(urllib.parse.urlparse(url).path)
    return filename or "unknown_file"

def is_youtube_or_social(url):
    for s in ['youtube.com', 'youtu.be', 'facebook.com', 'fb.watch', 'tiktok.com']:
        if s in url:
            return True
    return False

class DownloadThread(QThread):
    progress = pyqtSignal(str, str, float, str, str, str, str)
    finished = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = urllib.parse.unquote(url)
        self._is_paused = False
        self._is_stopped = False
        self._current_file = None

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def run(self):
        if is_youtube_or_social(self.url):
            category_folder = os.path.join(DOWNLOAD_ROOT, CATEGORY_LABELS['Video'])
            os.makedirs(category_folder, exist_ok=True)
            ydl_opts = {
                'outtmpl': os.path.join(category_folder, '%(title)s.%(ext)s'),
                'progress_hooks': [self.ytdlp_hook],
                'noplaylist': True,
                'concurrent_fragment_downloads': 16,
                'retries': 5,
                'force_overwrite': True,
                'continuedl': True,
                'cookiefile': r'D:\NhuanTinIDM\cookies.txt',
            }
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.url])
            except Exception as e:
                self.progress.emit("ERROR", "-", 0, f"Lỗi: {e}", "-", "-", "-")
                self.finished.emit("ERROR")
            return
        try:
            filename = os.path.basename(urllib.parse.urlparse(self.url).path) or "unknown_file"
            save_path = get_save_path(filename)
            self._current_file = save_path
            if os.path.exists(save_path):
                os.remove(save_path)
            fast_download(self.url, save_path)
            status = "Completed"
            size_str = "-"
            cat = get_category(filename)
            cat_label = CATEGORY_LABELS[cat] if cat else ""
            self.progress.emit(filename, size_str, 100, status, "-", "-", cat_label)
            self.finished.emit(filename)
        except Exception as e:
            self.progress.emit("ERROR", "-", 0, f"Lỗi: {e}", "-", "-", "")
            self.finished.emit("ERROR")

    if len(sys.argv) > 1:
        url = sys.argv[1]
        if url.startswith("idmapp://download?url="):
            link = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['url'][0]
            print("Nhận link:", link)
    
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
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded/total*100) if total else 0
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            size_str = f"{round(total/1024/1024,2)} MB" if total else "-"
            speed_str = f"{round(speed/1024,2)} KB/sec" if speed else "-"
            time_left = format_seconds(eta) if eta else "-"
            cat = get_category(filename_show)
            cat_label = CATEGORY_LABELS[cat] if cat else ""
            self.progress.emit(
                filename_show, size_str, percent, "Downloading", time_left, speed_str, cat_label
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
            size_str = "-"
            cat = get_category(filename_show)
            cat_label = CATEGORY_LABELS[cat] if cat else ""
            self.progress.emit(
                filename_show, size_str, 100, "Completed", "-", "-", cat_label
            )
            self.finished.emit(filename_show)

    def stop(self):
        self._is_stopped = True

class DownloadManager(QMainWindow):
    add_link_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDM Pikachu")
        try:
            self.setWindowIcon(QIcon("app.png"))
        except:
            pass
        self.resize(950, 500)

        # --- Đặt toàn bộ phần dựng giao diện ở đây ---
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels([L['category']])
        all_item = QTreeWidgetItem([L['all_downloads']])
        self.category_items = {"All Downloads": all_item}
        for cat in CATEGORIES:
            item = QTreeWidgetItem([CATEGORY_LABELS[cat]])
            all_item.addChild(item)
            self.category_items[cat] = item
        self.category_tree.addTopLevelItem(all_item)
        all_item.setExpanded(True)
        self.category_tree.clicked.connect(self.filter_by_category)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            L['filename'], L['size'], L['status'], L['time_left'], L['transfer_rate'], L['category']
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.link_label = QLabel(L['download_link'])
        self.link_input = QLineEdit()
        self.add_btn = QPushButton(L['add_url'])
        self.add_btn.clicked.connect(self.handle_add_link)
        self.pause_btn = QPushButton(L['pause'])
        self.pause_btn.clicked.connect(self.handle_pause)
        self.resume_btn = QPushButton(L['resume'])
        self.resume_btn.clicked.connect(self.handle_resume)
        self.clear_btn = QPushButton(L['delete'])
        self.clear_btn.clicked.connect(self.clear_selected)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.resume_btn)
        btn_row.addWidget(self.clear_btn)

        input_row = QHBoxLayout()
        input_row.addWidget(self.link_label)
        input_row.addWidget(self.link_input)

        right_layout = QVBoxLayout()
        right_layout.addLayout(input_row)
        right_layout.addLayout(btn_row)
        right_layout.addWidget(self.table)

        splitter = QSplitter()
        left_widget = QWidget()
        left_vbox = QVBoxLayout()
        left_vbox.addWidget(self.category_tree)
        left_widget.setLayout(left_vbox)
        splitter.addWidget(left_widget)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        splitter.setSizes([180, 700])

        container = QWidget()
        c_layout = QHBoxLayout()
        c_layout.addWidget(splitter)
        container.setLayout(c_layout)
        self.setCentralWidget(container)

        self.downloads = []  # [(thread, row)]
        self.active_rows = {}  # filename -> row
        self.row_category = {}  # row -> category

        # Connect signal
        self.add_link_signal.connect(self._handle_add_link_slot)

    def _handle_add_link_slot(self, link):
        print(f"Slot nhận link: {link}")
        self.link_input.setText(link)
        self.handle_add_link()

    def handle_add_link(self):
        url = self.link_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Lỗi", "Bạn chưa nhập liên kết!")
            return
        try:
            thread = DownloadThread(url)
            row = self.table.rowCount()
            self.table.insertRow(row)
            filename = url if is_youtube_or_social(url) else os.path.basename(urllib.parse.urlparse(url).path) or "unknown_file"
            cat = get_category(filename)
            cat_label = CATEGORY_LABELS[cat] if cat else ""
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
        except Exception as ex:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi thêm liên kết:\n{ex}")

    def update_row(self, row, filename, size, percent, status, time_left, speed, cat_label):
        if status == 'Downloading':
            status_text = f"{percent:.2f}% ({L['downloading']})"
        elif status == 'Completed':
            status_text = L['completed']
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
                    t.stop()
                    if is_youtube_or_social(t.url):
                        t.terminate()  # Force kill yt-dlp thread

    def handle_resume(self):
        for idx in self.table.selectionModel().selectedRows():
            row = idx.row()
            for t, r in self.downloads:
                if r == row:
                    if is_youtube_or_social(t.url):
                        if t.isRunning():
                            QMessageBox.information(self, "Đang tải", "Video đang tải, không cần tiếp tục.")
                        else:
                            # Tạo thread mới cho yt-dlp, yt-dlp sẽ tự resume nếu file tạm còn
                            new_thread = DownloadThread(t.url)
                            self.downloads.append((new_thread, row))
                            new_thread.progress.connect(lambda *info, row=row: self.update_row(row, *info))
                            new_thread.finished.connect(lambda fname: self.finish_row(fname))
                            new_thread.start()
                    else:
                        t.resume()

    def clear_selected(self):
        selected = sorted([idx.row() for idx in self.table.selectionModel().selectedRows()], reverse=True)
        for row in selected:
            for t, r in self.downloads:
                if r == row:
                    t.stop()
                    if is_youtube_or_social(t.url):
                        t.terminate()
            self.table.removeRow(row)

    def filter_by_category(self):
        item = self.category_tree.currentItem()
        if not item: return
        cat_label = item.text(0)
        if cat_label == "All Downloads":
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
        else:
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, self.row_category.get(row, "") != cat_label)

    def closeEvent(self, event):
        for t, _ in self.downloads:
            t.stop()
            t.quit()
            t.wait()
        event.accept()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        if send_to_running_app(url):
            sys.exit(0)

    threading.Thread(target=server, daemon=True).start()
    app = QApplication(sys.argv)
    win = DownloadManager()
    main_window = win
    win.show()
    if len(sys.argv) > 1:
        process_link(sys.argv[1])
    sys.exit(app.exec_())