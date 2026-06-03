(function () {
  function normalizeApiBase(value) {
    let base = String(value || "").trim().replace(/\/+$/, "");
    if (base.endsWith("/api")) base = base.slice(0, -4);
    return base;
  }

  const API_BASE = normalizeApiBase(window.API_BASE || "");
  const TOKEN_KEY = "anochat_token";

  function token() {
    return localStorage.getItem(TOKEN_KEY);
  }

  async function request(path, options) {
    const headers = Object.assign({}, options && options.headers ? options.headers : {});
    if (!(options && options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    if (token()) headers.Authorization = "Bearer " + token();
    let response;
    try {
      response = await fetch(API_BASE + path, Object.assign({}, options || {}, { headers }));
    } catch (err) {
      const missingConfig = !API_BASE && location.hostname.endsWith("vercel.app");
      throw new Error(missingConfig
        ? "Frontend API URL is missing. Add VERCEL_API_BASE in Vercel and redeploy."
        : "Cannot reach the backend. Check the backend URL and CORS settings.");
    }
    if (!response.ok) {
      let detail = response.statusText;
      try { detail = (await response.json()).detail || detail; } catch (_) {}
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
