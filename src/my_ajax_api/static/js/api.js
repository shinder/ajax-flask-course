// 統一的 fetch 封裝：帶 token、檢查 res.ok、解析 JSON、把錯誤包成帶 status 與 data 的 Error。
// 注意：這裡固定送 Content-Type: application/json，所以「不能」拿來上傳 FormData，
// 檔案上傳請直接用 fetch 或 XHR（見 upload.html）。
const BASE_URL = '';   // 同源，不需要指定主機

async function apiFetch(path, options = {}) {
    const token = localStorage.getItem('token');

    const res = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...options.headers
        }
    });

    if (res.status === 401) {
        // token 失效就清掉；要不要顯示登入提示或導向登入頁，由各頁面自行決定（見 index.html、login.html）
        localStorage.removeItem('token');
    }

    if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const err = new Error(errBody.title ?? `HTTP ${res.status}`);
        err.status = res.status;
        err.data = errBody;
        throw err;
    }

    if (res.status === 204) return null;
    return res.json();
}

export const api = {
    get:    (path, options) => apiFetch(path, options),   // options 可帶 signal 以便取消請求
    post:   (path, body) => apiFetch(path, { method: 'POST',   body: JSON.stringify(body) }),
    put:    (path, body) => apiFetch(path, { method: 'PUT',    body: JSON.stringify(body) }),
    patch:  (path, body) => apiFetch(path, { method: 'PATCH',  body: JSON.stringify(body) }),
    delete: (path, options) => apiFetch(path, { method: 'DELETE', ...options })
};
