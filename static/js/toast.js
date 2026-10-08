// 浮出的提示訊息，3 秒後自動消失。
// type 對應 style.css 的 .toast--success、.toast--error、.toast--info
export function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;   // textContent 不會把訊息當 HTML，避免 XSS
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
