// 把字串中的 HTML 特殊字元跳脫，塞進 innerHTML 才不會被當成標籤執行（防 XSS）。
// API 回來的資料是「別人輸入的」，不能信任；顯示前一律先跳脫。
export function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }[c]));
}

// 防抖：連續呼叫時只在「最後一次呼叫後 delay 毫秒」真正執行一次。
// 用在搜尋框：使用者打字時不要每個字元都發一次請求。
export function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}
