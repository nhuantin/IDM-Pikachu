function sendToApp(link) {
    // Gọi app qua custom protocol, không cần server
    window.open("idmapp://download?url=" + encodeURIComponent(link));
}

function findMainVideo() {
    let videos = Array.from(document.querySelectorAll('video')).filter(v => v.offsetWidth > 0 && v.offsetHeight > 0);
    if (videos.length === 0) return null;
    return videos.reduce((a, b) => (a.videoWidth * a.videoHeight > b.videoWidth * b.videoHeight ? a : b));
}

function createIdmButton(video) {
    // Nếu đã có nút thì thôi
    if (document.getElementById('idm-download-btn')) return;

    // Tạo div bọc nút (đảm bảo luôn nổi trên video)
    let overlay = document.createElement('div');
    overlay.id = 'idm-download-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = (video.getBoundingClientRect().top + window.scrollY - 25) + 'px';
    overlay.style.left = (video.getBoundingClientRect().left + window.scrollX + video.offsetWidth - 160) + 'px';
    overlay.style.zIndex = 99999;
    overlay.style.pointerEvents = 'none'; // overlay không nhận chuột, chỉ có button nhận
    overlay.style.width = '162px'; // chỉnh cho hợp lý với nút
    overlay.style.height = '38px';

    let btn = document.createElement('button');
    btn.id = 'idm-download-btn';
    btn.innerText = '▶️ Tải video này';
    btn.style.position = 'absolute';
    btn.style.top = '0px';
    btn.style.right = '0px';
    btn.style.background = '#fff';
    btn.style.border = '1px solid #888';
    btn.style.padding = '2px 12px';
    btn.style.borderRadius = '2px';
    btn.style.cursor = 'pointer';
    btn.style.fontWeight = 'bold';
    btn.style.boxShadow = '0 2px 2px #0002';
    btn.style.pointerEvents = 'auto'; // chỉ nút nhận chuột

    btn.onclick = function(e) {
        e.stopPropagation();
        let src = video.currentSrc;
        if (!src || src.startsWith("blob:")) {
            // Nếu là YouTube, gửi luôn URL trang (location.href)
            if (location.hostname.includes("youtube.com")) {
                sendToApp(location.href);
                btn.innerText = '✅ Đã gửi!';
                setTimeout(() => { btn.innerText = '▶️ Tải video này'; }, 1500);
                return;
            }
            alert("Không lấy được link thực của video này!\nBạn cần dùng trình duyệt hỗ trợ hoặc extension chuyên dụng cho YouTube.");
            return;
        }
        // Gửi link trực tiếp về app
        sendToApp(src);
        btn.innerText = '✅ Đã gửi!';
        setTimeout(() => { btn.innerText = '▶️ Tải video này'; }, 1500);
    };

    overlay.appendChild(btn);
    document.body.appendChild(overlay);

    // Di chuyển overlay theo video khi cuộn trang (nếu cần)
    window.addEventListener('scroll', function moveOverlay() {
        let rect = video.getBoundingClientRect();
        overlay.style.top = (rect.top + window.scrollY + 8) + 'px';
        overlay.style.left = (rect.left + window.scrollX + video.offsetWidth - 170) + 'px';
    });
}

function injectButtonIfNeeded() {
    let video = findMainVideo();
    if (video) createIdmButton(video);
}
setInterval(injectButtonIfNeeded, 1500);
