console.log("Background worker started");

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if ((msg.idmDownload && msg.videoSrc) || (msg.popupDownload && msg.url)) {
        let videoUrl = msg.videoSrc || msg.url;
        try {
            let urlObj = new URL(videoUrl);
            chrome.cookies.getAll({domain: urlObj.hostname}, function(cookies) {
                let cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join("; ");
                console.log("Gửi fetch tới app:", videoUrl, cookieHeader);
                fetch("http://127.0.0.1:5678/add-link", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        url: videoUrl,
                        cookies: cookieHeader
                    })
                })
                .then(() => {
                    chrome.notifications.create({
                        type: "basic",
                        iconUrl: "icon16.png",
                        title: "IDM Pikachu",
                        message: "Đã gửi link về ứng dụng tải!"
                    });
                })
                .catch(err => {
                    console.error("Fetch error:", err);
                });
            });
        } catch (e) {
            console.error("Error in onMessage:", e);
        }
        sendResponse({ok: true});
        return true;
    }
});

// Đăng ký context menu khi extension cài xong
chrome.runtime.onInstalled.addListener(() => {
  console.log("onInstalled: tạo context menu");
  chrome.contextMenus.create({
    id: "idm-download-video",
    title: "Tải video này bằng IDM Pikachu",
    contexts: ["video"]
  });
});

// Lắng nghe sự kiện khi chọn context menu
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "idm-download-video") {
	sendToApp(info.srcUrl);
    chrome.tabs.sendMessage(tab.id, {idmDownload: true, videoSrc: info.srcUrl});
  }
});