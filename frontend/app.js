// Общие утилиты
const API_BASE = 'http://localhost:8000/api/v1';

// Функция для выполнения аутентифицированных запросов
async function authFetch(url, options = {}) {
    const token = localStorage.getItem('accessToken');
    if (!token) {
        window.location.href = '/login.html';
        throw new Error('Not authenticated');
    }
    const headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        // Попытка обновить токен
        const refreshed = await refreshToken();
        if (refreshed) {
            // Повторить запрос с новым токеном
            const newToken = localStorage.getItem('accessToken');
            headers['Authorization'] = `Bearer ${newToken}`;
            return fetch(url, { ...options, headers });
        } else {
            localStorage.clear();
            window.location.href = '/login.html';
            throw new Error('Session expired');
        }
    }
    return response;
}

async function refreshToken() {
    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            credentials: 'include'
        });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('accessToken', data.access_token);
            return true;
        }
    } catch (e) {}
    return false;
}

// Выход
async function logout() {
    try {
        await authFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    } catch (e) {}
    localStorage.removeItem('accessToken');
    localStorage.removeItem('userEmail');
    window.location.href = '/login.html';
}

// Привязка к глобальному объекту для использования в HTML
window.logout = logout;