/**
 * Small shared helpers used by index.html, dashboard.html and History.html
 * to talk to the FastAPI backend (Backend/app/api/routes.py). No build step
 * / framework - plain fetch, kept deliberately simple to match the existing
 * static frontend.
 */
(function () {
  const BASE = window.API_BASE_URL || "http://localhost:8000";

  async function apiRequest(path, options) {
    let response;
    try {
      response = await fetch(BASE + path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
    } catch (networkError) {
      throw new Error(
        `Could not reach the backend at ${BASE}. Is it running? (uvicorn main:app --reload --port 8000)`
      );
    }

    let data = null;
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (_e) {
        data = null;
      }
    }

    if (!response.ok) {
      const detail = data && data.detail ? data.detail : response.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function statusClass(status) {
    switch ((status || "").toUpperCase()) {
      case "DELIVERED":
      case "SENT":
        return "delivered";
      case "PENDING":
        return "pending";
      case "FAILED":
        return "failed";
      default:
        return "";
    }
  }

  function statusLabel(status) {
    const s = (status || "").toUpperCase();
    if (s === "SENT") return "Delivered";
    if (s === "DELIVERED") return "Delivered";
    if (s === "PENDING") return "Pending";
    if (s === "FAILED") return "Failed";
    return status || "Unknown";
  }

  function overallStatus(notification) {
    const statuses = (notification.deliveries || []).map((d) => d.status);
    if (statuses.length === 0) return "PENDING";
    if (statuses.some((s) => s === "FAILED")) return "FAILED";
    if (statuses.every((s) => s === "SENT" || s === "DELIVERED")) return "DELIVERED";
    return "PENDING";
  }

  function formatTime(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return isoString;
    return date.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
    ));
  }

  window.NotificationApi = {
    health: () => apiRequest("/health"),
    createNotification: (payload) =>
      apiRequest("/api/notifications", { method: "POST", body: JSON.stringify(payload) }),
    listNotifications: (params) => {
      const query = new URLSearchParams();
      Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") query.set(key, value);
      });
      const qs = query.toString();
      return apiRequest("/api/notifications" + (qs ? `?${qs}` : ""));
    },
    getStats: () => apiRequest("/api/stats"),
    retryNotification: (id) => apiRequest(`/api/notifications/${id}/retry`, { method: "POST" }),
  };

  window.NotificationUi = { statusClass, statusLabel, overallStatus, formatTime, escapeHtml };
})();
