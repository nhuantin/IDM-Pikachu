// Đóng popup khi bấm nút X
document.getElementById('close-btn').onclick = () => window.close();

// Hàm tạo section tiêu đề
function createSection(title, icon) {
  return `<div class="section-title"><i>${icon}</i>${title}</div>`;
}

// Hàm tạo option, truyền đủ thông tin cần thiết
function createOption(option, type) {
  // option: {label, info, url, format_id, ext, bitrate, lang}
  let attrs = [
    `data-url="${encodeURIComponent(option.url)}"`,
    `data-type="${type}"`
  ];
  if (option.format_id) attrs.push(`data-format_id="${option.format_id}"`);
  if (option.ext) attrs.push(`data-target_ext="${option.ext}"`);
  if (option.bitrate) attrs.push(`data-bitrate="${option.bitrate}"`);
  if (option.lang) attrs.push(`data-lang="${option.lang}"`);
  return `<div class="option-item" ${attrs.join(' ')}>
    <span class="option-label">${option.label}</span>
    <span class="option-info">${option.info || ""}</span>
  </div>`;
}

// Nhận dữ liệu từ background
chrome.runtime.sendMessage({action: 'getDownloadOptions'}, function(response) {
  let html = '';
  if (response.video && response.video.length) {
    html += createSection('VIDEO', '📺');
    html += '<div class="option-list">';
    response.video.forEach(opt => {
      html += createOption(opt, 'video');
    });
    html += '</div>';
  }
  if (response.audio && response.audio.length) {
    html += createSection('AUDIO', '🎵');
    html += '<div class="option-list">';
    response.audio.forEach(opt => {
      html += createOption(opt, 'audio');
    });
    html += '</div>';
  }
  if (response.subtitle && response.subtitle.length) {
    html += createSection('PHỤ ĐỀ', '≡');
    html += '<div class="option-list">';
    response.subtitle.forEach(opt => {
      html += createOption(opt, 'subtitle');
    });
    html += '</div>';
  }
  document.getElementById('file-list').innerHTML = html;

  // Gửi về app desktop khi chọn
  document.querySelectorAll('.option-item').forEach(el => {
    el.onclick = function() {
      const url = decodeURIComponent(this.getAttribute('data-url'));
      const type = this.getAttribute('data-type');
      const format_id = this.getAttribute('data-format_id');
      const target_ext = this.getAttribute('data-target_ext');
      const bitrate = this.getAttribute('data-bitrate');
      const lang = this.getAttribute('data-lang');
      // Gửi đủ thông tin về app (qua background)
      chrome.runtime.sendMessage({
        action: 'downloadWithApp',
        url,
        type,
        format_id,
        target_ext,
        bitrate,
        lang
      });
      window.close();
    }
  });
});
