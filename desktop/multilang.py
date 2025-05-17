import locale

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
        'category': 'Danh mục',
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

lang_code = (locale.getlocale()[0] or 'en').split('_')[0].lower()
if lang_code not in LANGUAGES:
    lang_code = 'en'
L = LANGUAGES[lang_code]