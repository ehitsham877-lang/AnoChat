(function () {
  function normalizeApiBase(value) {
    let base = String(value || "").trim().replace(/\/+$/, "");
    if (base.endsWith("/api")) base = base.slice(0, -4);
    return base;
  }

  const API_BASE = normalizeApiBase(window.API_BASE || "");
  const TOKEN_KEY = "anochat_token";
  const REQUEST_TIMEOUT_MS = 15000;

  function token() {
    return localStorage.getItem(TOKEN_KEY);
  }

  async function request(path, options) {
    const headers = Object.assign({}, options && options.headers ? options.headers : {});
    if (!(options && options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    if (token()) headers.Authorization = "Bearer " + token();
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    let response;
    try {
      response = await fetch(API_BASE + path, Object.assign({}, options || {}, { headers, signal: controller.signal }));
    } catch (err) {
      if (err && err.name === "AbortError") {
        throw new Error("Backend request timed out. Check the backend URL and try again.");
      }
      const missingConfig = !API_BASE && location.hostname.endsWith("vercel.app");
      throw new Error(missingConfig
        ? "Frontend API URL is missing. Add VERCEL_API_BASE in Vercel and redeploy."
        : "Cannot reach the backend. Check the backend URL and CORS settings.");
    } finally {
      window.clearTimeout(timeout);
    }
    if (!response.ok) {
      let detail = response.statusText;
      try { detail = (await response.json()).detail || detail; } catch (_) {}
      if (response.status === 404 && !API_BASE && location.hostname.endsWith("vercel.app")) {
        throw new Error("Frontend is calling Vercel instead of the backend. Add VERCEL_API_BASE in Vercel and redeploy.");
      }
      if (response.status === 404 && path.indexOf("/api/auth/login") === 0) {
        throw new Error(`Login API not found at ${API_BASE || location.origin}${path}. Check VERCEL_API_BASE; include the gateway prefix if your backend uses one.`);
      }
      if (response.status === 401 && path.indexOf("/api/auth/login") !== 0) {
        localStorage.removeItem(TOKEN_KEY);
        window.dispatchEvent(new CustomEvent("anochat_session_expired", { detail }));
      }
      throw new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : (detail || `Request failed with ${response.status}`));
    }
    const type = response.headers.get("content-type") || "";
    return type.indexOf("application/json") >= 0 ? response.json() : response.blob();
  }

  window.apiClient = {
    setToken: (value) => localStorage.setItem(TOKEN_KEY, value),
    clearToken: () => localStorage.removeItem(TOKEN_KEY),
    token,
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body || {}) }),
    put: (path, body) => request(path, { method: "PUT", body: JSON.stringify(body || {}) }),
    del: (path) => request(path, { method: "DELETE" }),
  };
})();
