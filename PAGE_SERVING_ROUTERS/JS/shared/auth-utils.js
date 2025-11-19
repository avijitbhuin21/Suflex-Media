export function handleLogout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('adminToken');
    localStorage.removeItem('userSession');
    sessionStorage.clear();
    deleteCookie('hashed_email');
    deleteCookie('hashed_password');
    window.location.href = '/login';
}

export function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

export function deleteCookie(name) {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
}

export function showLoading(show) {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        if (show) {
            loadingOverlay.classList.remove('hidden');
        } else {
            loadingOverlay.classList.add('hidden');
        }
    }
}

export async function verifyAuth() {
    const hashedEmail = getCookie('hashed_email');
    const hashedPassword = getCookie('hashed_password');
    
    if (!hashedEmail || !hashedPassword) {
        setTimeout(() => {
            window.location.href = "/login";
        }, 1000);
        return false;
    }

    try {
        const res = await fetch("/api/auto-login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                hashed_email: hashedEmail,
                hashed_password: hashedPassword
            }),
            credentials: 'include'
        });

        if (!res.ok) {
            deleteCookie('hashed_email');
            deleteCookie('hashed_password');
            localStorage.removeItem('authToken');
            setTimeout(() => {
                window.location.href = "/login";
            }, 1000);
            return false;
        }

        const data = await res.json().catch(() => null);
        if (data && data.status === "success") {
            if (data.access_token) {
                localStorage.setItem('authToken', data.access_token);
            }
            showLoading(false);
            return true;
        } else {
            deleteCookie('hashed_email');
            deleteCookie('hashed_password');
            localStorage.removeItem('authToken');
            setTimeout(() => {
                window.location.href = "/login";
            }, 1000);
            return false;
        }
    } catch (err) {
        localStorage.removeItem('authToken');
        setTimeout(() => {
            window.location.href = "/login";
        }, 1000);
        return false;
    }
}

export function getAuthToken() {
    return localStorage.getItem('authToken');
}

export async function authenticatedFetch(url, options = {}) {
    const token = getAuthToken();
    
    if (!token) {
        window.location.href = "/login";
        throw new Error("No authentication token found");
    }
    
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    if (response.status === 401 || response.status === 403) {
        localStorage.removeItem('authToken');
        deleteCookie('hashed_email');
        deleteCookie('hashed_password');
        window.location.href = "/login";
        throw new Error("Authentication failed");
    }
    
    return response;
}

export function initAuth() {
    showLoading(true);
    verifyAuth();
}