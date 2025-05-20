// Ví dụ giả lập lấy link video/audio/subtitle
function getOptions() {
  // Xử lý thực tế cần lấy từ player response YouTube hoặc API khác
  return {
    video: [
      {label: "Full HD", info: "1080p60 .mp4", url: "https://...", type: "video"},
      {label: "HD", info: "720p60 .mp4", url: "https://...", type: "video"},
      {label: "Trung bình⚡", info: "360p .mp4", url: "https://...", type: "video"},
      {label: "Di động", info: "144p .mp4", url: "https://...", type: "video"}
    ],
    audio: [
      {label: "Trung bình⚡", info: ".mp3", url: "https://...", type: "audio"},
      {label: "Trung bình", info: "128kbps .mp3", url: "https://...", type: "audio"}
    ],
    subtitle: [
      {label: "Tiếng Anh", info: ".srt", url: "https://...", type: "subtitle"},
      {label: "Tiếng Việt", info: ".srt", url: "https://...", type: "subtitle"}
    ]
  };
}

// Khi load trang YouTube, gửi về background
chrome.runtime.sendMessage({
  action: 'setDownloadOptions',
  data: getOptions()
});

// NÚT NỔI GIỐNG IDM - CÓ GHI CHÚ ĐỂ DỄ ĐIỀU CHỈNH
function insertIDMButtonOnVideo(videoEl) {
  // Xóa nút cũ trên body nếu có
  let oldBtn = document.getElementById('idm-pikachu-btn-global');
  if (oldBtn) oldBtn.remove();

  // Lấy vị trí tuyệt đối của video trên trang
  const rect = videoEl.getBoundingClientRect();

  // Tạo nút nổi trên body
  const btn = document.createElement('div');
  btn.id = 'idm-pikachu-btn-global';
  btn.className = 'idm-pikachu-btn-onvideo';
  btn.style.position = 'fixed';
  btn.style.top = (rect.top - 26) + 'px'; // Đẩy nút lên trên ngoài video
  btn.style.left = (rect.right - 180) + 'px'; // Đặt nút sát mép phải video, chỉnh 140 cho vừa nút
  btn.style.zIndex = '2147483647';
  btn.style.background = 'linear-gradient(180deg, #eaf6ff 0%, #c3d9ef 100%)';
  btn.style.border = '1px solid #b0c4de';
  btn.style.borderRadius = '6px';
  btn.style.boxShadow = '0 2px 8px #b0c4de77';
  btn.style.display = 'flex';
  btn.style.alignItems = 'center';
  btn.style.padding = '2px 8px 2px 6px';
  btn.style.height = '20px';
  btn.style.fontFamily = 'Segoe UI, Arial, sans-serif';
  btn.style.userSelect = 'none';
  btn.style.cursor = 'pointer';
  btn.style.fontSize = '1em';

  btn.innerHTML = `
    <img src="${chrome.runtime.getURL('icon16.png')}" style="width:20px;height:20px;margin-right:6px;" />
    <span style="color:#2176b8;font-weight:bold;font-size:1.5em;margin-right:10px;">Tải video này</span>
    <button id="idm-pikachu-btn-help" style="width:20px;height:20px;border:none;background:linear-gradient(180deg,#f8f8f8,#e0e0e0);border-radius:50%;margin-left:0px;margin-right:2px;cursor:pointer;font-size:1em;color:#2176b8;box-shadow:0 0px 0px #b0c4de55;">?</button>
    <button id="idm-pikachu-btn-x" style="width:20px;height:20px;border:none;background:linear-gradient(180deg,#f8f8f8,#e0e0e0);border-radius:50%;margin-right:-2px;cursor:pointer;font-size:1em;color:#888;box-shadow:0 0px 0px #b0c4de55;">&times;</button>
  `;

  btn.onclick = function(e) {
    if (e.target.id === 'idm-pikachu-btn-x') {
      btn.remove();
      return;
    }
    e.stopPropagation();
    showQualityOverlayFromApp(window.location.href);
  };

  document.body.appendChild(btn);

  // Xử lý mouseleave: khi rời khỏi video và nút thì xóa nút
  function removeBtnIfOut() {
    setTimeout(() => {
      if (!videoEl.matches(':hover') && !btn.matches(':hover')) {
        btn.remove();
      }
    }, 80);
  }
  videoEl.addEventListener('mouseleave', removeBtnIfOut);
  btn.addEventListener('mouseleave', removeBtnIfOut);
}

// Gọi khi vào /watch và khi chuyển video (SPA)
// (ĐÃ VÔ HIỆU HÓA để tránh chèn trùng nút)
// if (location.hostname.includes('youtube.com') && location.pathname.startsWith('/watch')) {
//   setTimeout(showIDMButtonOnMainPlayer, 1000);
//   const observer = new MutationObserver(showIDMButtonOnMainPlayer);
//   observer.observe(document.body, {childList: true, subtree: true});
// }

// Thêm hàm polling lấy formats
function fetchFormatsWithPolling(videoUrl, onResult) {
  fetch(`http://127.0.0.1:5678/formats?url=${encodeURIComponent(videoUrl)}`)
    .then(res => res.json())
    .then(options => {
      if (options.status === 'pending') {
        setTimeout(() => fetchFormatsWithPolling(videoUrl, onResult), 400);
      } else {
        onResult(options);
      }
    })
    .catch(() => {
      alert('Không lấy được danh sách chất lượng từ app. Hãy chắc chắn app đang chạy!');
    });
}

// Sửa showQualityOverlayFromApp để dùng polling
function showQualityOverlayFromApp(videoUrl) {
  if (document.getElementById('idm-pikachu-overlay')) return;
  // Hiện popup loading ngay khi bắt đầu polling
  const overlay = document.createElement('div');
  overlay.id = 'idm-pikachu-overlay';
  overlay.style.position = 'fixed';
  overlay.style.top = '-30';
  overlay.style.left = '0';
  overlay.style.width = '100vw';
  overlay.style.height = '100vh';
  overlay.style.background = 'rgba(0,0,0,0.25)';
  overlay.style.zIndex = '10000';
  overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
  const box = document.createElement('div');
  box.style.background = '#fff';
  box.style.borderRadius = '12px';
  box.style.padding = '24px 32px 24px 32px';
  box.style.minWidth = '180px';
  box.style.maxWidth = '340px';
  box.style.margin = '60px auto 0 auto';
  box.style.boxShadow = '0 4px 24px rgba(0,0,0,0.18)';
  box.style.position = 'relative';
  box.style.top = '60px';
  box.style.maxHeight = '80vh';
  box.style.overflowY = 'auto';
  box.style.display = 'flex';
  box.style.flexDirection = 'column';
  box.style.alignItems = 'center';
  box.innerHTML = `<div style="font-size:1.1em;font-weight:bold;margin-bottom:10px;">Đang lấy danh sách chất lượng...</div><div class="idm-pikachu-spinner" style="margin:10px auto;width:32px;height:32px;border:4px solid #eee;border-top:4px solid #2176b8;border-radius:50%;animation:spin 1s linear infinite;"></div>`;
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  // Thêm CSS cho spinner nếu chưa có
  if (!document.getElementById('idm-pikachu-spinner-style')) {
    const style = document.createElement('style');
    style.id = 'idm-pikachu-spinner-style';
    style.innerHTML = `@keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}`;
    document.head.appendChild(style);
  }
  // Polling formats
  fetchFormatsWithPolling(videoUrl, function(options) {
    overlay.remove(); // Xóa popup loading
    // Tạo nhóm Video có tiếng bằng cách ghép video_only với audio tốt nhất
    let videoWithAudio = [];
    if (options.video_only && options.audio) {
      options.video_only.forEach(v => {
        if (!v.format_id) {
          console.error('Thiếu format_id ở video_only:', v);
          return;
        }
        // Chỉ lấy các chất lượng video có tiếng mong muốn
        const allowedLabels = [
          '144p', '240p', '360p', '480p', '720p60', '1080p60', '1440p602k', '2160p604k'
        ];
        if (!allowedLabels.some(label => v.label.includes(label))) return;
        // Ưu tiên audio ext là m4a (AAC)
        let best_audio = null;
        let best_abr = 0;
        options.audio.forEach(a => {
          if (!a.format_id) {
            console.error('Thiếu format_id ở audio:', a);
            return;
          }
          if (a.ext === 'm4a') {
            let abr = parseInt(a.label);
            if (!isNaN(abr) && abr > best_abr) {
              best_abr = abr;
              best_audio = a;
            }
          }
        });
        // Nếu không có m4a, lấy audio ext khác
        if (!best_audio) {
          options.audio.forEach(a => {
            if (!a.format_id) {
              console.error('Thiếu format_id ở audio:', a);
              return;
            }
            let abr = parseInt(a.label);
            if (!isNaN(abr) && abr > best_abr) {
              best_abr = abr;
              best_audio = a;
            }
          });
        }
        if (best_audio) {
          videoWithAudio.push({
            label: v.label + ' (có tiếng)',
            ext: v.ext,
            filesize: v.filesize,
            format_id: v.format_id + '+' + best_audio.format_id
          });
        }
      });
    }
    const overlay2 = document.createElement('div');
    overlay2.id = 'idm-pikachu-overlay';
    overlay2.style.position = 'fixed';
    overlay2.style.top = '-30';
    overlay2.style.left = '0';
    overlay2.style.width = '100vw';
    overlay2.style.height = '100vh';
    overlay2.style.background = 'rgba(0,0,0,0.25)';
    overlay2.style.zIndex = '10000';
    overlay2.onclick = function(e) { if (e.target === overlay2) overlay2.remove(); };
    const box2 = document.createElement('div');
    box2.style.background = '#fff';
    box2.style.borderRadius = '12px';
    box2.style.padding = '14px 16px 10px 16px';
    box2.style.minWidth = '180px';
    box2.style.maxWidth = '340px';
    box2.style.margin = '60px auto 0 auto';
    box2.style.boxShadow = '0 4px 24px rgba(0,0,0,0.18)';
    box2.style.position = 'relative';
    box2.style.top = '60px';
    box2.style.maxHeight = '80vh';
    box2.style.overflowY = 'auto';
    box2.style.display = 'flex';
    box2.style.flexDirection = 'column';
    box2.style.alignItems = 'stretch';
    let html = '<div style="font-weight:bold;font-size:1.08em;margin-bottom:8px;">Chọn chất lượng để tải</div>';
    if (videoWithAudio.length) {
      html += '<div style="margin:8px 0 4px 0;font-weight:600;">Video có tiếng</div>';
      videoWithAudio.forEach((opt, idx) => {
        html += `<div class="idm-pikachu-qitem" data-type="video_with_audio" data-idx="${idx}" style="padding:7px 0;cursor:pointer;border-bottom:1px solid #eee;">${opt.label} <span style='color:#888;font-size:0.95em;'>${opt.ext||''} ${opt.filesize ? (opt.filesize+'MB') : ''}</span></div>`;
      });
    }
    // Hiện các lựa chọn âm thanh với bitrate và định dạng mong muốn
    const allowedBitrates = [32, 64, 128, 192, 256, 320];
    const allowedAudioExts = ['mp3', 'm4a', 'ogg'];
    if (options.audio && options.audio.length) {
      html += '<div style="margin:12px 0 4px 0;font-weight:600;">Audio</div>';
      options.audio.forEach((opt, idx) => {
        if (!allowedAudioExts.includes(opt.ext)) return;
        let abr = parseInt(opt.label);
        if (!allowedBitrates.includes(abr)) return;
        html += `<div class="idm-pikachu-qitem" data-type="audio" data-idx="${idx}" data-mp3="0" style="padding:7px 0;cursor:pointer;border-bottom:1px solid #eee;">
          ${opt.label}kbps <span style='color:#888;font-size:0.95em;'>.${opt.ext||''} ${opt.filesize ? (opt.filesize+'MB') : ''}</span>
        </div>`;
      });
      // Thêm các lựa chọn mp3 convert từ audio gốc tốt nhất
      const bestAudio = options.audio.find(a => a.ext === 'm4a') || options.audio[0];
      allowedBitrates.forEach(bitrate => {
        html += `<div class="idm-pikachu-qitem" data-type="audio" data-idx="0" data-mp3="1" data-bitrate="${bitrate}" style="padding:7px 0;cursor:pointer;border-bottom:1px solid #eee;">
          ${bitrate}kbps <span style='color:#888;font-size:0.95em;'>.mp3 (convert)</span>
        </div>`;
      });
    }
    html += '<div style="text-align:right;margin-top:10px;"><button id="idm-pikachu-closebtn" style="padding:5px 14px;border-radius:6px;border:none;background:#eee;cursor:pointer;font-weight:bold;">Đóng</button></div>';
    box2.innerHTML = html;
    overlay2.appendChild(box2);
    document.body.appendChild(overlay2);

    document.getElementById('idm-pikachu-closebtn').onclick = () => overlay2.remove();

    box2.querySelectorAll('.idm-pikachu-qitem').forEach(el => {
      el.onclick = function(e) {
        const type = this.getAttribute('data-type');
        const idx = parseInt(this.getAttribute('data-idx'));
        const isMp3 = this.getAttribute('data-mp3') === '1';
        let opt = null;
        if (type === 'video_with_audio') opt = videoWithAudio[idx];
        if (type === 'audio') opt = options.audio[idx];
        if (isMp3) {
          // Tạo lựa chọn mp3 convert từ audio gốc tốt nhất
          const bestAudio = options.audio.find(a => a.ext === 'm4a') || options.audio[0];
          opt = {...bestAudio};
          opt.ext = 'mp3';
          opt.bitrate = this.getAttribute('data-bitrate');
        }
        if (!opt || !opt.format_id) {
          alert('Không đủ thông tin để tải (thiếu format_id).');
          console.error('Không có format_id cho lựa chọn:', opt);
          return;
        }
        let target_ext = opt.ext || null;
        let bitrate = opt.bitrate || null;
        fetch('http://127.0.0.1:5678/add-link', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            url: videoUrl,
            type: (type === 'audio' || isMp3) ? 'audio' : 'video',
            format_id: opt.format_id,
            target_ext: target_ext,
            bitrate: bitrate,
            lang: opt.lang || null
          })
        });
        overlay2.remove();
      }
    });
  });
}

// === BỔ SUNG: Hiện nút IDM khi hover vào video/thumbnail trên mọi trang YouTube ===
if (location.hostname.includes('youtube.com')) {
  function addHoverIDMButtonForAllVideos() {
    // Chọn tất cả video/thumbnail có thể xem được
    const videoSelectors = [
     'ytd-thumbnail',
      'ytd-grid-video-renderer',
      'ytd-watch-flexy video',
      'video.html5-main-video',
      'ytd-player video',
    ];
    const allVideos = Array.from(document.querySelectorAll(videoSelectors.join(',')));
    allVideos.forEach(videoEl => {
      // Tránh gắn nhiều lần
      if (videoEl._idmHoverBinded) return;
      videoEl._idmHoverBinded = true;
      // Gắn sự kiện hover
      videoEl.addEventListener('mouseenter', function(e) {
        insertIDMButtonOnVideo(videoEl);
      });
      videoEl.addEventListener('mouseleave', function(e) {
        setTimeout(() => {
          let parent = videoEl.closest('.ytd-thumbnail, .ytd-rich-item-renderer, .ytd-video-renderer, .ytd-playlist-video-renderer');
          if (!parent) parent = videoEl.parentElement;
          const btn = parent && parent.querySelector('.idm-pikachu-btn-onvideo');
          if (btn && !btn.matches(':hover')) btn.remove();
        }, 80);
      });
    });
  }
  // Chạy lần đầu
  setTimeout(addHoverIDMButtonForAllVideos, 1000);
  // Theo dõi DOM thay đổi để gắn cho video mới xuất hiện
  const observer = new MutationObserver(() => {
    addHoverIDMButtonForAllVideos();
  });
  observer.observe(document.body, {childList: true, subtree: true});
}

// === Danh sách đuôi file nhận diện giống app ===
const FILE_EXTS = [
  // Video
  '.mp4', '.mkv', '.avi', '.mov', '.webm', '.3gp', '.m4v', '.mpeg', '.mpg', '.wmv', '.asf', '.ogv', '.rm', '.rmvb', '.qt',
  // Music
  '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.aif', '.ra', '.wma',
  // Documents
  '.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.ppt', '.pps', '.tif', '.tiff', '.plj',
  // Programs
  '.exe', '.msi', '.apk', '.iso', '.img', '.bin', '.msu',
  // Compressed
  '.zip', '.rar', '.7z', '.tar.gz', '.gz', '.bz2', '.gzip', '.tar', '.z', '.ace', '.arj', '.lzh', '.sit', '.sitx', '.sea'
];
function isDownloadFile(url) {
  return FILE_EXTS.some(ext => url.toLowerCase().endsWith(ext));
}
function isDownloadButton(el) {
  if (!el) return false;
  const text = (el.innerText || '').toLowerCase();
  const aria = (el.getAttribute && el.getAttribute('aria-label') || '').toLowerCase();
  const classes = (typeof el.className === 'string' ? el.className : '').toLowerCase();
  return (
    text.includes('tải xuống') || text.includes('download') ||
    aria.includes('download') ||
    classes.includes('download')
  );
}
function getDownloadLink(el) {
  if (el.tagName === 'A' && el.href) return el.href;
  let a = el.querySelector && el.querySelector('a[href]');
  if (a) return a.href;
  let dataLink = el.getAttribute && (el.getAttribute('data-link') || el.getAttribute('data-download-url'));
  if (dataLink) return dataLink;
  return null;
}
document.addEventListener('click', function(e) {
  let el = e.target;
  while (el && el !== document.body) {
    if (isDownloadButton(el)) {
      let link = getDownloadLink(el);
      if (link && isDownloadFile(link)) {
        e.preventDefault();
        e.stopPropagation();
        sendToIDMPikachu(link);
      }
      // Nếu không lấy được link hoặc link không đúng loại file, KHÔNG gửi request, KHÔNG alert
      return false;
    }
    el = el.parentElement;
  }
}, true);
function sendToIDMPikachu(url) {
  fetch('http://127.0.0.1:5678/add-link', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      url: url,
      type: 'auto'
    })
  });
}

// Khi trang YouTube có ?getcookies=1, gửi yêu cầu lấy cookies về app
if (window.location.hostname.includes('youtube.com') && window.location.search.includes('getcookies=1')) {
  chrome.runtime.sendMessage({action: 'sendYoutubeCookiesToApp'});
}
