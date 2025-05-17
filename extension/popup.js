document.addEventListener('DOMContentLoaded', async () => {
    const optionsList = document.getElementById('options-list');
    const closeBtn = document.getElementById('close-btn');
    closeBtn.onclick = () => window.close();

    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        let url = tabs[0].url;
        fetch("http://127.0.0.1:5678/formats?url=" + encodeURIComponent(url))
            .then(res => res.json())
            .then(data => {
                optionsList.innerHTML = "";

                // VIDEO
                if (data.video && data.video.length) {
                    optionsList.innerHTML += `<div class="section"><span class="icon">📺</span> <span class="section-title">VIDEO</span></div>`;
                    data.video.forEach(f => {
                        optionsList.innerHTML += `<div class="option" data-type="video" data-id="${f.format_id}"><span class="option-label">${f.label}</span><span class="option-ext">${f.ext || ".mp4"}</span></div>`;
                    });
                }
                // AUDIO
                if (data.audio && data.audio.length) {
                    optionsList.innerHTML += `<div class="section"><span class="icon">🎵</span> <span class="section-title">AUDIO</span></div>`;
                    data.audio.forEach(f => {
                        optionsList.innerHTML += `<div class="option" data-type="audio" data-id="${f.format_id}"><span class="option-label">${f.label}</span><span class="option-ext">${f.ext || ".mp3"}</span></div>`;
                    });
                }
                // SUBTITLES
                if (data.subtitles && data.subtitles.length) {
                    optionsList.innerHTML += `<div class="section"><span class="icon">📝</span> <span class="section-title">PHỤ ĐỀ</span></div>`;
                    data.subtitles.forEach(s => {
                        optionsList.innerHTML += `<div class="option" data-type="subtitle" data-lang="${s.lang}"><span class="option-label">${s.label}</span><span class="option-ext">.srt</span></div>`;
                    });
                }

                // Bắt sự kiện click
                document.querySelectorAll('.option').forEach(opt => {
                    opt.onclick = () => {
                        const type = opt.dataset.type;
                        let body = {url, type};
                        if (type === "video" || type === "audio") body.format_id = opt.dataset.id;
                        if (type === "subtitle") body.lang = opt.dataset.lang;
                        fetch("http://127.0.0.1:5678/download", {
                            method: "POST",
                            headers: {"Content-Type": "application/json"},
                            body: JSON.stringify(body)
                        });
                        opt.innerText = "✅ Đã gửi tải!";
                        setTimeout(() => window.close(), 1200);
                    }
                });
            })
            .catch(() => optionsList.innerHTML = "Không lấy được thông tin định dạng!");
    });
});
