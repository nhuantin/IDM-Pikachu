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
                if (data.video.length) {
                    optionsList.innerHTML += "<h4>🎬 VIDEO</h4>";
                    data.video.forEach(f => {
                        optionsList.innerHTML += `<div class="option" data-type="video" data-id="${f.format_id}">
                            ${f.label} (${f.filesize} MB)
                        </div>`;
                    });
                }
                if (data.audio.length) {
                    optionsList.innerHTML += "<h4>🎵 AUDIO</h4>";
                    data.audio.forEach(f => {
                        optionsList.innerHTML += `<div class="option" data-type="audio" data-id="${f.format_id}">
                            ${f.label} (${f.filesize} MB)
                        </div>`;
                    });
                }
                if (data.subtitles.length) {
                    optionsList.innerHTML += "<h4>📝 PHỤ ĐỀ</h4>";
                    data.subtitles.forEach(s => {
                        optionsList.innerHTML += `<div class="option" data-type="subtitle" data-lang="${s.lang}">
                            ${s.label} (.srt)
                        </div>`;
                    });
                }
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