(function () {
  const app = document.getElementById("app");
  const navItems = [
    { key: "dashboard", label: "Dashboard", icon: "LayoutDashboard" },
    { key: "projects", label: "Projects", icon: "FolderKanban" },
    { key: "chatters", label: "Chatter", icon: "MessagesSquare" },
    { key: "monitoring", label: "Monitoring", icon: "Activity" },
    { key: "users", label: "Users & Roles", icon: "Users" },
    { key: "settings", label: "Settings", icon: "Settings" },
  ];

  const state = {
    tab: localStorage.getItem("anochat_tab") || "dashboard",
    theme: localStorage.getItem("anochat_theme") || "light",
    sidebarCollapsed: localStorage.getItem("anochat_sidebar") === "collapsed",
    mobileSidebarOpen: false,
    bootstrapping: !!apiClient.token(),
    loading: false,
    user: null,
    users: [],
    projects: [],
    chatters: [],
    messages: [],
    notifications: [],
    notificationsOpen: false,
    pushConfig: null,
    notificationPreferences: null,
    pushBusy: false,
    presenceOpen: false,
    presenceSyncTimer: null,
    messageSyncTimer: null,
    refreshingMessages: false,
    lastMessageSignature: "",
    files: [],
    activityLogs: [],
    emailLogs: [],
    stats: null,
    operations: { tasks: [], documents: [], incidents: [], knowledge: [] },
    activeChatter: storedActiveChatterId(),
    chatterInfoOpen: true,
    chatInfoExpanded: { members: false, images: false, documents: false },
    scrollMessagesBottom: false,
    sendingMessage: false,
    composerBody: "",
    pendingAttachment: null,
    pendingVoiceDuration: null,
    pendingVoicePreviewUrl: null,
    voiceRecording: null,
    replyTo: null,
    editingMessage: null,
    editingBody: "",
    typingUsers: [],
    lastTypingPingAt: 0,
    mention: { open: false, query: "" },
    openMessageMenu: null,
    renderCycle: 0,
    filters: { projectSearch: "", projectStatus: "all", projectPriority: "all", logSearch: "", logType: "all", userSearch: "", chatterSearch: "" },
    modal: null,
    toasts: [],
    attachmentPreviews: {},
    loadingPreviews: new Set(),
    audioPreviews: {},
    audioState: {},
    loadingAudio: new Set(),
  };

  function storedActiveChatterId() {
    const raw = localStorage.getItem("anochat_active_chatter");
    const id = Number(raw);
    return raw && Number.isFinite(id) && id > 0 ? id : null;
  }

  function sameId(a, b) {
    if (a === null || a === undefined || b === null || b === undefined) return false;
    return Number(a) === Number(b);
  }

  function setActiveChatter(id) {
    const nextId = Number(id);
    if (Number.isFinite(nextId) && nextId > 0) {
      state.activeChatter = nextId;
      localStorage.setItem("anochat_active_chatter", String(nextId));
      return;
    }
    clearActiveChatter();
  }

  function clearActiveChatter() {
    state.activeChatter = null;
    localStorage.removeItem("anochat_active_chatter");
  }

  function h(tag, props, children) {
    const el = document.createElement(tag);
    Object.entries(props || {}).forEach(([key, value]) => {
      if (key === "class") el.className = value;
      else if (key === "html") el.innerHTML = value;
      else if (key.startsWith("on")) el.addEventListener(key.slice(2).toLowerCase(), value);
      else if (value !== null && value !== undefined && value !== false) el.setAttribute(key, value === true ? "" : value);
    });
    (Array.isArray(children) ? children : [children]).filter((child) => child !== null && child !== undefined).forEach((child) => {
      el.appendChild(typeof child === "string" || typeof child === "number" ? document.createTextNode(String(child)) : child);
    });
    return el;
  }

  function icon(name, size) {
    const map = {
      Activity: '<path d="M22 12h-4l-3 8L9 4l-3 8H2"/>',
      Bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
      BellOff: '<path d="M13.73 21a2 2 0 0 1-3.46 0"/><path d="M18.63 13A17.89 17.89 0 0 1 18 8"/><path d="M6.26 6.26A5.99 5.99 0 0 0 6 8c0 7-3 7-3 9h14"/><path d="m2 2 20 20"/>',
      Boxes: '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
      Calendar: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
      Check: '<path d="M20 6 9 17l-5-5"/>',
      ChevronLeft: '<path d="m15 18-6-6 6-6"/>',
      ChevronRight: '<path d="m9 18 6-6-6-6"/>',
      ChevronsUpDown: '<path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/>',
      Download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
      Edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
      Eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
      FolderKanban: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/><path d="M8 10v4"/><path d="M12 10v2"/><path d="M16 10v6"/>',
      HelpCircle: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 1 1 5.8 1c0 2-3 2-3 4"/><path d="M12 17h.01"/>',
      Image: '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
      Lock: '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
      LayoutDashboard: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
      LogOut: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
      Mail: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-10 6L2 7"/>',
      MailCheck: '<path d="M22 13V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h8"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/><path d="m16 19 2 2 4-4"/>',
      Menu: '<path d="M4 12h16"/><path d="M4 6h16"/><path d="M4 18h16"/>',
      Mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
      MessageCircle: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
      MessagesSquare: '<path d="M14 9a2 2 0 0 1-2 2H6l-4 4V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2z"/><path d="M18 9h2a2 2 0 0 1 2 2v10l-4-4h-6a2 2 0 0 1-2-2v-1"/>',
      Moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
      Paperclip: '<path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.82-2.83l8.49-8.48"/>',
      Pause: '<rect width="4" height="16" x="6" y="4" rx="1"/><rect width="4" height="16" x="14" y="4" rx="1"/>',
      Play: '<polygon points="6 3 20 12 6 21 6 3"/>',
      Plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
      RadioTower: '<path d="M4.9 16.1a10 10 0 0 1 0-8.2"/><path d="M7.8 13.2a5 5 0 0 1 0-4.4"/><circle cx="12" cy="11" r="2"/><path d="m12 13 4 8"/><path d="m12 13-4 8"/><path d="M16.2 13.2a5 5 0 0 0 0-4.4"/><path d="M19.1 16.1a10 10 0 0 0 0-8.2"/>',
      MoreVertical: '<circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>',
      Phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.08 4.18 2 2 0 0 1 4.06 2h3a2 2 0 0 1 2 1.72c.12.9.32 1.77.58 2.61a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.47-1.1a2 2 0 0 1 2.11-.45c.84.26 1.71.46 2.61.58A2 2 0 0 1 22 16.92Z"/>',
      Tag: '<path d="M12.6 2H4a2 2 0 0 0-2 2v8.6a2 2 0 0 0 .6 1.4l7.4 7.4a2 2 0 0 0 2.8 0l8.6-8.6a2 2 0 0 0 0-2.8L14 2.6A2 2 0 0 0 12.6 2Z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
      Search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
      Send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
      Settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.72l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"/><circle cx="12" cy="12" r="3"/>',
      ShieldCheck: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.68 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
      Sparkles: '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>',
      Square: '<rect width="14" height="14" x="5" y="5" rx="2"/>',
      Sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
      Trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="m19 6-1 14H6L5 6"/>',
      UserPlus: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M22 11h-6"/>',
      UserRound: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
      Users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
      X: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    };
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    Object.entries({
      class: "icon",
      width: size || 18,
      height: size || 18,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    }).forEach(([key, value]) => svg.setAttribute(key, value));
    svg.innerHTML = map[name] || "";
    return svg;
  }

  function roles(user) { return (user && user.roles ? user.roles : []).map((role) => role.name); }
  function isAdmin() { return roles(state.user).indexOf("admin") >= 0; }
  function canManage() { return isAdmin(); }
  function canCreateChatter() { return isAdmin(); }
  function canDeleteChatter(chatter) { return !!chatter && isAdmin(); }
  function idInList(ids, id) { return (ids || []).map(Number).indexOf(Number(id)) >= 0; }
  function chatterIsReadOnly(chatter) {
    if (!state.user) return false;
    if (state.user.read_only) return true;
    if (idInList(chatter?.read_only_member_ids, state.user.id)) return true;
    const project = chatter?.project_id ? state.projects.find((item) => Number(item.id) === Number(chatter.project_id)) : null;
    return idInList(project?.read_only_member_ids, state.user.id);
  }
  function activeChatterIsReadOnly() {
    return chatterIsReadOnly(state.chatters.find((item) => Number(item.id) === Number(state.activeChatter)));
  }
  function availableNavItems() {
    if (isAdmin()) return navItems;
    return navItems.filter((item) => ["dashboard", "projects", "chatters", "settings"].indexOf(item.key) >= 0);
  }
  function roleLabel(role) {
    const labels = { admin: "Admin", manager: "Project Manager", staff: "Project Manager", developer: "Developer", customer: "Customer" };
    return labels[String(role || "").toLowerCase()] || cap(role);
  }
  function normalizeRole(role) { return String(role || "").toLowerCase() === "staff" ? "manager" : String(role || "customer").toLowerCase(); }
  function displayRoles(user) { return roles(user).map(roleLabel); }
  function roleOptions() {
    return [
      { value: "customer", label: "Customer" },
      { value: "developer", label: "Developer" },
      { value: "manager", label: "Project Manager" },
      { value: "admin", label: "Admin" },
    ];
  }

  function render() {
    state.renderCycle += 1;
    const renderCycle = state.renderCycle;
    const messageScrollTop = captureMessageScrollTop();
    const composerFocus = captureComposerFocus();
    const searchFocus = captureSearchFocus();
    const shouldScrollMessagesBottom = state.scrollMessagesBottom;
    state.scrollMessagesBottom = false;
    const visibleNav = state.user ? availableNavItems() : navItems;
    if (!visibleNav.some((item) => item.key === state.tab)) {
      state.tab = "dashboard";
      localStorage.setItem("anochat_tab", state.tab);
    }
    document.documentElement.dataset.theme = state.theme;
    document.documentElement.dataset.tab = state.tab;
    app.innerHTML = "";
    if (state.bootstrapping && apiClient.token() && !state.user) {
      app.appendChild(bootView());
      app.appendChild(toastRegion());
      return;
    }
    if (!apiClient.token() || !state.user) {
      app.appendChild(loginView());
      app.appendChild(toastRegion());
      return;
    }
    app.appendChild(h("div", { class: shellClass() }, [
      sidebar(),
      h("div", { class: "mobile-scrim", onclick: () => { state.mobileSidebarOpen = false; render(); } }),
      h("div", { class: "main-shell" }, [mobileMenuTrigger(), notices(), currentView()]),
      state.modal ? modalView() : null,
      toastRegion(),
    ]));
    afterRender(messageScrollTop, shouldScrollMessagesBottom, renderCycle, composerFocus, searchFocus);
    ensureVisibleImagePreviews();
    ensureVisibleAudioPreviews();
  }

  function captureMessageScrollTop() {
    if (state.tab !== "chatters") return null;
    const stream = document.querySelector(".message-stream");
    return stream ? stream.scrollTop : null;
  }

  function captureComposerFocus() {
    const input = document.activeElement;
    if (!input || !input.matches?.(".composer input[name='body']")) return null;
    return {
      value: input.value,
      start: input.selectionStart,
      end: input.selectionEnd,
    };
  }

  function captureSearchFocus() {
    const input = document.activeElement;
    if (!input || !input.matches?.(".search-box input[data-search-key]")) return null;
    return {
      key: input.dataset.searchKey,
      start: input.selectionStart,
      end: input.selectionEnd,
    };
  }

  function afterRender(messageScrollTop, shouldScrollMessagesBottom, renderCycle, composerFocus, searchFocus) {
    window.requestAnimationFrame(() => {
      if (renderCycle !== state.renderCycle) return;
      if (state.modal?.type === "user") {
        document.querySelectorAll(".user-modal-form input").forEach((input) => {
          if (!input.dataset.cleanRender) {
            input.value = "";
            input.dataset.cleanRender = "1";
          }
        });
      }
      restoreSearchFocus(searchFocus);
      const stream = document.querySelector(".message-stream");
      if (!stream) {
        restoreComposerFocus(composerFocus);
        return;
      }
      if (shouldScrollMessagesBottom) {
        stream.scrollTop = stream.scrollHeight;
        restoreComposerFocus(composerFocus);
        return;
      }
      if (messageScrollTop !== null && messageScrollTop !== undefined) {
        stream.scrollTop = Math.min(messageScrollTop, stream.scrollHeight);
      }
      restoreComposerFocus(composerFocus);
    });
  }

  function restoreSearchFocus(searchFocus) {
    if (!searchFocus || state.modal) return;
    const input = document.querySelector(`.search-box input[data-search-key="${searchFocus.key}"]`);
    if (!input) return;
    input.focus({ preventScroll: true });
    if (document.activeElement !== input) return;
    const position = Math.min(input.value.length, searchFocus.start ?? input.value.length);
    const end = Math.min(input.value.length, searchFocus.end ?? position);
    input.setSelectionRange(position, end);
  }

  function restoreComposerFocus(composerFocus) {
    if (!composerFocus || state.modal) return;
    const input = document.querySelector(".composer input[name='body']");
    if (!input) return;
    input.focus({ preventScroll: true });
    if (document.activeElement !== input) return;
    const position = Math.min(input.value.length, composerFocus.start ?? input.value.length);
    const end = Math.min(input.value.length, composerFocus.end ?? position);
    input.setSelectionRange(position, end);
  }

  function isAudioPlaying() {
    return Array.from(document.querySelectorAll("audio[data-audio-key]")).some((audio) => !audio.paused && !audio.ended);
  }

  function shellClass() {
    return [
      "workspace-shell",
      state.sidebarCollapsed ? "collapsed" : "",
      state.mobileSidebarOpen ? "mobile-open" : "",
      state.loading ? "is-loading" : "",
    ].join(" ");
  }

  function loginView() {
    return h("main", { class: "login-page" }, [
      h("section", { class: "login-hero" }, [
        h("span", { class: "hero-orb hero-orb-top" }),
        h("span", { class: "hero-orb hero-orb-bottom" }),
        h("div", { class: "brand-row" }, [h("span", { class: "brand-mark" }, "A"), h("span", {}, "AnoChat")]),
        h("span", { class: "hero-pill" }, [icon("Sparkles", 16), "All-in-one. All yours."]),
        h("div", {}, [
          h("h1", { html: "Your workspace,<br><span>one sign-in</span> away." }),
          h("p", { class: "hero-copy" }, "Access projects, chatter threads, files, users, monitoring, and operations from the standalone workspace."),
        ]),
        h("div", { class: "role-grid" }, [
          roleCard("Admin", "Full workspace control", "ShieldCheck"),
          roleCard("Project Manager", "Projects and teams", "Users"),
          roleCard("Customer", "Assigned portal access", "UserPlus"),
        ]),
        h("div", { class: "login-footnote" }, [icon("Lock", 18), "Secure. Reliable. Built for teams."]),
      ]),
      h("form", { class: "login-card", onsubmit: login }, [
        h("div", { class: "login-shield" }, [icon("ShieldCheck", 24)]),
        h("h2", {}, "Welcome back"),
        h("p", { class: "muted" }, "Sign in to your workspace account"),
        state.toasts.filter((toast) => toast.type === "error").slice(-1).map((toast) => h("div", { class: "inline-alert" }, toast.message))[0] || null,
        loginField("Login / Email", "Mail", h("input", { name: "login", placeholder: "Enter your email", autocomplete: "username", oninput: clearLoginError })),
        loginField("Password", "Lock", h("input", { id: "login-password", name: "password", type: "password", placeholder: "Enter your password", autocomplete: "current-password", oninput: clearLoginError }), h("button", { type: "button", class: "password-eye", onclick: togglePassword }, [icon("Eye", 18)])),
        h("button", { class: "btn btn-primary btn-block login-submit" }, [icon("LogOut", 18), "Log in to portal"]),
      ]),
    ]);
  }

  function bootView() {
    return h("main", { class: "boot-screen" }, [
      h("div", { class: "boot-card" }, [
        h("div", { class: "brand-row" }, [h("span", { class: "brand-mark" }, "A"), h("strong", {}, "AnoChat")]),
        h("div", { class: "boot-loader" }),
        h("h1", {}, "Opening workspace"),
        h("p", { class: "muted" }, "Restoring your signed-in session..."),
      ]),
    ]);
  }

  function roleCard(title, text, iconName) {
    return h("div", { class: "role-card" }, [
      h("span", { class: "role-icon" }, [icon(iconName, 24)]),
      h("span", { class: "role-copy" }, [h("strong", {}, title), h("small", {}, text)]),
    ]);
  }

  function loginField(label, iconName, input, action) {
    return h("label", { class: "login-field" }, [
      h("span", {}, label),
      h("div", { class: "login-input-wrap" }, [icon(iconName), input, action || null]),
    ]);
  }

  function togglePassword() {
    const input = document.getElementById("login-password");
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
  }

  function sidebar() {
    return h("aside", { class: "sidebar" }, [
      h("div", { class: "sidebar-head" }, [
        h("div", { class: "sidebar-brand" }, [h("span", { class: "sidebar-logo" }, [icon("MessageCircle", 24)]), h("span", { class: "brand-text" }, "AnoChat")]),
        h("button", { class: "sidebar-collapse desktop-only", onclick: toggleSidebar, title: "Collapse sidebar" }, [icon(state.sidebarCollapsed ? "ChevronRight" : "ChevronLeft", 18)]),
        h("button", { class: "icon-btn mobile-only", onclick: () => { state.mobileSidebarOpen = false; render(); }, title: "Close menu" }, [icon("X")]),
      ]),
      h("nav", { class: "nav-list" }, availableNavItems().map((item) => h("button", {
        class: state.tab === item.key ? "nav-link active" : "nav-link",
        onclick: () => switchTab(item.key),
        title: item.label,
      }, [icon(item.icon), h("span", { class: "nav-label" }, [h("span", {}, item.label), navNotificationBadge(item.key)]), navNotificationDot(item.key)]))),
    ]);
  }

  function mobileMenuTrigger() {
    return h("button", {
      class: "mobile-menu-trigger mobile-only",
      onclick: () => { state.mobileSidebarOpen = true; render(); },
      title: "Open menu",
      "aria-label": "Open menu",
    }, [icon("Menu")]);
  }

  function presenceControl() {
    const status = state.user?.messenger_status || "offline";
    return h("div", { class: "presence-wrap" }, [
      h("button", { class: `icon-btn presence-btn presence-${status}`, title: `Presence: ${cap(status)}`, onclick: togglePresenceMenu }, [icon("RadioTower"), h("span", { class: "presence-btn-dot" })]),
      state.presenceOpen ? h("div", { class: "presence-menu" }, ["online", "away", "busy", "offline"].map((value) => h("button", {
        type: "button",
        class: value === status ? "presence-option active" : "presence-option",
        onclick: () => savePresenceStatus(value),
      }, [h("span", { class: `presence-dot presence-${value}` }), h("span", {}, cap(value)), value === status ? icon("Check", 14) : null]))) : null,
    ]);
  }

  function togglePresenceMenu(event) {
    if (event) event.preventDefault();
    state.presenceOpen = !state.presenceOpen;
    render();
  }

  function navNotificationBadge(key) {
    const count = moduleBadgeCount(key);
    return count ? h("span", { class: "nav-badge", title: `${count} unread notification${count === 1 ? "" : "s"}` }, count) : null;
  }

  function navNotificationDot(key) {
    return moduleBadgeCount(key) ? h("span", { class: "nav-dot", "aria-hidden": "true" }) : null;
  }

  function moduleBadgeCount(key) {
    if (key === "chatters") {
      return state.chatters.reduce((total, chatter) => total + Number(chatter.unread_count || 0), 0);
    }
    return 0;
  }

  function moduleNotificationCount(key) {
    return state.notifications.filter((item) => !item.is_read && notificationModuleKey(item) === key).length;
  }

  function sidebarBadgeSignature() {
    return availableNavItems().map((item) => `${item.key}:${moduleBadgeCount(item.key)}`).join("|");
  }

  function notificationModuleKey(item) {
    const text = [item.title, item.body].join(" ").toLowerCase();
    if (/\b(chatter|conversation|message|chat|attachment|file)\b/.test(text)) return "chatters";
    if (/\b(project|invoice|deadline|task)\b/.test(text)) return "projects";
    if (/\b(user|role|account|access|customer|developer|manager)\b/.test(text)) return "users";
    if (/\b(login|audit|activity|monitor|operation|system)\b/.test(text)) return "monitoring";
    return "dashboard";
  }

  function notificationIcon(item) {
    const key = notificationModuleKey(item);
    if (key === "chatters") return "MessagesSquare";
    if (key === "projects") return "FolderKanban";
    if (key === "users") return "Users";
    if (key === "monitoring") return "Activity";
    return "Bell";
  }

  function pageSubtitle() {
    const map = {
      dashboard: "Overview, quick actions, and recent workspace activity.",
      projects: "Manage project records, status, priority, ownership, and assignments.",
      chatters: "Modern project conversation workspace with messages and attachments.",
      monitoring: "Scan activity and audit records without losing context.",
      users: "Create users, adjust roles, and manage access.",
      settings: "Manage appearance, notifications, profile details, and sign out.",
    };
    return map[state.tab] || "";
  }

  function notices() {
    return h("div", { class: "notice-wrap" }, [
      state.loading ? h("div", { class: "loading-bar" }, "Loading...") : null,
      state.error ? h("div", { class: "alert alert-error" }, state.error) : null,
    ]);
  }

  function currentView() {
    if (state.tab === "projects") return projectsView();
    if (state.tab === "chatters") return chattersView();
    if (state.tab === "monitoring") return monitoringView();
    if (state.tab === "users") return usersView();
    if (state.tab === "settings") return settingsView();
    return dashboardView();
  }

  async function run(fn, success) {
    state.loading = true;
    state.error = "";
    render();
    try {
      await fn();
      if (apiClient.token() && state.user) await refreshSidebarBadges();
      if (success) toast(success, "success");
    } catch (err) {
      const message = err.message || String(err);
      state.error = message;
      toast(message, "error");
    } finally {
      state.loading = false;
      render();
    }
  }

  function toast(message, type) {
    const id = Date.now() + Math.random();
    state.toasts.push({ id, message, type: type || "success" });
    window.setTimeout(() => {
      state.toasts = state.toasts.filter((item) => item.id !== id);
      render();
    }, 3200);
  }

  function toastRegion() {
    return h("div", { class: "toast-region" }, state.toasts.map((item) => h("div", { class: `toast ${item.type}` }, [icon(item.type === "error" ? "X" : "Check"), h("span", {}, item.message)])));
  }

  function broadcastPresenceChange(user) {
    if (!user?.id) return;
    localStorage.setItem("anochat_presence_changed", JSON.stringify({
      user_id: user.id,
      status: user.messenger_status || "offline",
      at: Date.now(),
    }));
  }

  async function login(event) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.target).entries());
    payload.login = String(payload.login || "").trim().toLowerCase();
    payload.password = String(payload.password || "").trim();
    if (!payload.login || !payload.password) {
      toast("Enter your login and password.", "error");
      render();
      return;
    }
    state.loading = true;
    state.error = "";
    render();
    try {
      const result = await apiClient.post("/api/auth/login", payload);
      apiClient.setToken(result.access_token);
      state.user = result.user;
      state.tab = "dashboard";
      clearActiveChatter();
      localStorage.setItem("anochat_tab", "dashboard");
      broadcastPresenceChange(state.user);
      startPresenceSync();
      startMessageSync();
      state.loading = false;
      toast("Signed in.", "success");
      render();
      loadWorkspaceAfterLogin();
    } catch (err) {
      const message = err.message || String(err);
      state.error = message;
      state.loading = false;
      toast(message, "error");
      render();
    }
  }

  async function loadWorkspaceAfterLogin() {
    try {
      await Promise.all([loadNotifications(), loadPushSettings(), loadTab(state.tab)]);
    } catch (err) {
      toast(err.message || "Workspace data is still loading. Please refresh if it does not appear.", "error");
    } finally {
      render();
    }
  }

  async function logout() {
    await run(async () => {
      const loggedOutUser = state.user;
      try { await apiClient.post("/api/auth/logout", {}); } catch (_) {}
      if (loggedOutUser) broadcastPresenceChange({ ...loggedOutUser, messenger_status: "offline" });
      cancelVoiceRecording(true);
      stopPresenceSync();
      stopMessageSync();
      apiClient.clearToken();
      clearActiveChatter();
      Object.assign(state, {
        user: null, users: [], projects: [], chatters: [], messages: [], notifications: [], files: [], typingUsers: [],
        pushConfig: null, notificationPreferences: null, pushBusy: false,
        activityLogs: [], emailLogs: [], stats: null, activeChatter: null, pendingAttachment: null, pendingVoiceDuration: null, pendingVoicePreviewUrl: null, replyTo: null, editingMessage: null, editingBody: "", modal: null,
        audioState: {},
        chatInfoExpanded: { members: false, images: false, documents: false },
        lastMessageSignature: "", refreshingMessages: false, lastTypingPingAt: 0,
        operations: { tasks: [], documents: [], incidents: [], knowledge: [] },
      });
    });
  }

  function clearLoginError() {
    state.toasts = state.toasts.filter((toast) => toast.type !== "error");
  }

  async function switchTab(tab) {
    if (!availableNavItems().some((item) => item.key === tab)) tab = "dashboard";
    if (state.tab === tab && !state.mobileSidebarOpen) return;
    state.mobileSidebarOpen = false;
    state.tab = tab;
    localStorage.setItem("anochat_tab", tab);
    state.loading = true;
    state.error = "";
    if (tab !== "chatters") {
      cancelVoiceRecording(true);
      state.replyTo = null;
      clearPendingVoiceNote();
      state.pendingVoiceDuration = null;
      state.editingMessage = null;
      state.editingBody = "";
    }
    render();
    window.scrollTo({ top: 0, behavior: "auto" });
    try {
      await loadTab(tab);
    } catch (err) {
      const message = err.message || String(err);
      state.error = message;
      toast(message, "error");
    } finally {
      state.loading = false;
      render();
    }
  }

  function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    localStorage.setItem("anochat_sidebar", state.sidebarCollapsed ? "collapsed" : "expanded");
    render();
  }

  function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem("anochat_theme", state.theme);
    render();
  }

  async function toggleNotifications() {
    state.notificationsOpen = !state.notificationsOpen;
    render();
    if (state.notificationsOpen) await refreshNotifications();
  }

  async function refreshNotifications() {
    try {
      await loadNotifications();
    } catch (err) {
      toast(err.message || "Could not load notifications.", "error");
    } finally {
      render();
    }
  }

  async function refreshSidebarBadges() {
    try {
      const [, chatters] = await Promise.all([
        loadNotifications(),
        apiClient.get("/api/chatters"),
      ]);
      state.chatters = chatters;
    } catch (_) {}
  }

  function startPresenceSync() {
    stopPresenceSync();
    state.presenceSyncTimer = window.setInterval(() => refreshPresenceData(true), 4000);
  }

  function stopPresenceSync() {
    if (state.presenceSyncTimer) window.clearInterval(state.presenceSyncTimer);
    state.presenceSyncTimer = null;
  }

  function startMessageSync() {
    stopMessageSync();
    state.messageSyncTimer = window.setInterval(() => refreshActiveChatterMessages(true), 3000);
  }

  function stopMessageSync() {
    if (state.messageSyncTimer) window.clearInterval(state.messageSyncTimer);
    state.messageSyncTimer = null;
    state.refreshingMessages = false;
  }

  function messageSignature(messages) {
    return JSON.stringify((messages || []).map((message) => [
      message.id,
      message.body,
      message.reply_to_id || "",
      message.reply_to_body || "",
      message.updated_at || message.created_at || "",
      message.can_edit || false,
      message.can_edit_until || "",
      message.is_deleted || false,
      (message.seen_by || []).map((user) => user.id).sort().join(","),
      (message.attachments || []).map((attachment) => attachment.id).join(","),
    ]));
  }

  function typingSignature(users) {
    return (users || []).map((user) => user.id).sort().join(",");
  }

  async function refreshActiveChatterMessages(silent) {
    if (!apiClient.token() || !state.user || state.tab !== "chatters" || !state.activeChatter || state.refreshingMessages || state.sendingMessage) return;
    const chatterId = state.activeChatter;
    const previousBadgeSignature = sidebarBadgeSignature();
    state.refreshingMessages = true;
    try {
      const [chatters, messages, notifications, typingUsers] = await Promise.all([
        apiClient.get("/api/chatters"),
        apiClient.get(`/api/chatters/${chatterId}/messages`),
        apiClient.get("/api/notifications"),
        loadTypingUsers(chatterId),
      ]);
      if (!sameId(state.activeChatter, chatterId) || state.tab !== "chatters") return;
      const nextSignature = messageSignature(messages);
      const previousCount = state.messages.length;
      const previousLast = state.messages[state.messages.length - 1]?.id || null;
      const nextLast = messages[messages.length - 1]?.id || null;
      const changed = nextSignature !== state.lastMessageSignature;
      const typingChanged = typingSignature(typingUsers) !== typingSignature(state.typingUsers);
      state.chatters = chatters;
      markChatterReadLocally(chatterId);
      state.notifications = notifications;
      state.typingUsers = typingUsers;
      const badgesChanged = sidebarBadgeSignature() !== previousBadgeSignature;
      if (changed) {
        state.messages = messages;
        state.lastMessageSignature = nextSignature;
        if (previousLast !== nextLast || messages.length > previousCount) state.scrollMessagesBottom = true;
        if (!isAudioPlaying()) render();
      } else if ((badgesChanged || typingChanged) && !isAudioPlaying()) {
        render();
      }
    } catch (err) {
      if (!silent) toast(err.message || "Could not refresh chatter messages.", "error");
    } finally {
      state.refreshingMessages = false;
    }
  }

  async function refreshPresenceData(silent) {
    if (!apiClient.token() || !state.user) return;
    try {
      const [me, users, chatters, notifications] = await Promise.all([
        apiClient.get("/api/auth/me"),
        apiClient.get("/api/users"),
        apiClient.get("/api/chatters"),
        apiClient.get("/api/notifications"),
      ]);
      state.user = me;
      state.users = users;
      state.chatters = chatters;
      state.notifications = notifications;
      if (state.activeChatter && !state.chatters.some((item) => Number(item.id) === Number(state.activeChatter))) {
        clearActiveChatter();
        state.messages = [];
        state.typingUsers = [];
        state.lastMessageSignature = "";
      }
      const shouldRenderPresence = state.tab !== "chatters" || !state.activeChatter || state.modal?.type === "profile";
      if (shouldRenderPresence && (!state.modal || state.modal.type === "profile") && !isAudioPlaying()) {
        if (state.modal?.type === "profile") state.modal = { type: "profile", data: me };
        render();
      }
    } catch (err) {
      if (!silent) toast(err.message || "Could not refresh presence.", "error");
    }
  }

  async function loadAll() {
    state.user = await apiClient.get("/api/auth/me");
    if (!availableNavItems().some((item) => item.key === state.tab)) {
      state.tab = "dashboard";
      localStorage.setItem("anochat_tab", state.tab);
    }
    await Promise.all([loadNotifications(), loadPushSettings(), loadTab(state.tab)]);
  }

  async function bootstrap() {
    state.bootstrapping = true;
    render();
    try {
      await loadAll();
      startPresenceSync();
      startMessageSync();
    } catch (err) {
      stopPresenceSync();
      stopMessageSync();
      apiClient.clearToken();
      Object.assign(state, {
        user: null, users: [], projects: [], chatters: [], messages: [], notifications: [], files: [], typingUsers: [],
        pushConfig: null, notificationPreferences: null, pushBusy: false,
        activityLogs: [], emailLogs: [], stats: null, activeChatter: null, pendingAttachment: null, pendingVoiceDuration: null, pendingVoicePreviewUrl: null, replyTo: null, editingMessage: null, editingBody: "", modal: null,
        audioState: {},
        lastMessageSignature: "", refreshingMessages: false, lastTypingPingAt: 0,
        operations: { tasks: [], documents: [], incidents: [], knowledge: [] },
      });
      toast("Session expired. Please sign in again.", "error");
    } finally {
      state.bootstrapping = false;
      state.loading = false;
      render();
    }
  }

  async function loadTab(tab) {
    if (tab === "dashboard") await Promise.all([loadUsers(), loadProjects(), loadChatters({ listOnly: true }), loadMonitoringSoft()]);
    if (tab === "projects") await Promise.all([loadUsers(), loadProjects()]);
    if (tab === "chatters") await Promise.all([loadUsers(), loadProjects(), loadChatters(), loadFiles()]);
    if (tab === "monitoring") await Promise.all([loadMonitoring(), loadChatters({ listOnly: true })]);
    if (tab === "users") await loadUsers();
  }

  async function loadUsers() { state.users = await apiClient.get("/api/users"); }
  async function loadNotifications() { state.notifications = await apiClient.get("/api/notifications"); }
  async function loadTypingUsers(chatterId) {
    if (!chatterId) return [];
    try {
      return await apiClient.get(`/api/chatters/${chatterId}/typing`);
    } catch (err) {
      return [];
    }
  }
  async function loadPushSettings() {
    try {
      const [config, preferences] = await Promise.all([
        apiClient.get("/api/notifications/push-config"),
        apiClient.get("/api/notifications/preferences"),
      ]);
      state.pushConfig = config;
      state.notificationPreferences = preferences;
    } catch (err) {
      state.pushConfig = { enabled: false, public_key: null };
      state.notificationPreferences = state.notificationPreferences || {
        browser_push_enabled: false,
        chatter_messages_enabled: true,
        workspace_updates_enabled: true,
        mentions_enabled: true,
      };
    }
  }
  async function loadProjects() { state.projects = await apiClient.get("/api/projects"); }
  async function loadFiles() { state.files = await apiClient.get("/api/attachments"); }
  async function loadChatters(options = {}) {
    state.chatters = await apiClient.get("/api/chatters");
    if (options.listOnly) return;
    if (state.activeChatter && !state.chatters.some((item) => Number(item.id) === Number(state.activeChatter))) {
      clearActiveChatter();
    }
    if (!state.activeChatter) {
      state.messages = [];
      state.typingUsers = [];
      state.lastMessageSignature = "";
      return;
    }
    state.messages = await apiClient.get(`/api/chatters/${state.activeChatter}/messages`);
    state.typingUsers = await loadTypingUsers(state.activeChatter);
    markChatterReadLocally(state.activeChatter);
    state.lastMessageSignature = messageSignature(state.messages);
  }

  function markChatterReadLocally(chatterId) {
    if (!chatterId) return;
    state.chatters = state.chatters.map((chatter) => (
      Number(chatter.id) === Number(chatterId) ? { ...chatter, unread_count: 0 } : chatter
    ));
  }
  async function loadMonitoringSoft() { if (canManage()) await loadMonitoring(); }
  async function loadMonitoring() {
    if (!canManage()) return;
    state.stats = await apiClient.get("/api/monitoring/stats");
    state.activityLogs = await apiClient.get("/api/activity-logs");
  }
  async function loadEmail() { if (canManage()) state.emailLogs = await apiClient.get("/api/email-logs"); }
  async function loadOperations() {
    const [tasks, documents, incidents, knowledge] = await Promise.all([
      apiClient.get("/api/operations/tasks"),
      apiClient.get("/api/operations/documents"),
      apiClient.get("/api/operations/incidents"),
      apiClient.get("/api/operations/knowledge"),
    ]);
    state.operations = { tasks, documents, incidents, knowledge };
  }

  function dashboardView() {
    const recent = state.activityLogs.slice(0, 6);
    const metrics = [
      metric("Projects", state.projects.length, "FolderKanban", "Active project records", "blue"),
      metric("Chatters", state.chatters.length, "MessagesSquare", "Open conversation spaces", "teal"),
    ].concat(isAdmin() ? [
      metric("Users", state.users.length, "Users", "Visible workspace users", "violet"),
      metric("Activity", state.activityLogs.length, "Activity", "Recent audit events", "amber"),
    ] : []);
    const actions = [
      canManage() ? quickAction("Create Project", "Start a new project record", "Plus", () => { state.tab = "projects"; openModal("project"); }) : null,
      quickAction("View Projects", "Open assigned project records", "FolderKanban", () => switchTab("projects")),
      quickAction("Open Chatter", "Jump into team messages", "MessagesSquare", () => switchTab("chatters")),
      isAdmin() ? quickAction("Manage Users", "Create and update roles", "UserPlus", () => switchTab("users")) : null,
    ].filter(Boolean);
    return page([
      h("section", { class: isAdmin() ? "dashboard-hero" : "dashboard-hero compact" }, [
        h("div", {}, [
          h("span", { class: "dashboard-pill" }, [icon("Sparkles", 14), "Premium workspace"]),
          h("h2", {}, `Welcome back, ${state.user?.name || "there"}`),
          h("p", {}, "A clean command center for your projects, chatter, monitoring, and team access."),
        ]),
        h("div", { class: "dashboard-hero-card" }, [
          h("span", {}, "Workspace health"),
          h("strong", {}, canManage() ? "Operational" : "Assigned access"),
          h("small", {}, `${state.projects.length} projects / ${state.chatters.length} chatters`),
        ]),
      ]),
      h("section", { class: isAdmin() ? "metric-grid dashboard-metrics" : "metric-grid dashboard-metrics compact" }, metrics),
      h("section", { class: isAdmin() ? "quick-actions" : "quick-actions compact" }, actions),
      h("section", { class: "content-grid two dashboard-content" }, [
        h("article", { class: "card dashboard-panel" }, [cardHeader("Recent Projects", "Latest project records", "Projects", () => switchTab("projects")), projectCards(filteredProjects().slice(0, 4), true)]),
        h("article", { class: "card dashboard-panel" }, [cardHeader("Active Chatter", "Current conversations", "Chatter", () => switchTab("chatters")), chatterList(5, true)]),
      ]),
      isAdmin() ? h("article", { class: "card dashboard-panel activity-panel" }, [cardHeader("Recent Activity", "Latest audit events"), activityList(recent)]) : null,
    ]);
  }

  function metric(label, value, iconName, subtitle, tone) {
    return h("article", { class: `metric-card tone-${tone || "blue"}` }, [
      h("div", { class: "metric-icon" }, [icon(iconName)]),
      h("div", {}, [h("span", {}, label), h("strong", {}, value), h("p", {}, subtitle)]),
    ]);
  }

  function quickAction(title, text, iconName, onClick) {
    return h("button", { class: "quick-card", onclick: onClick }, [
      h("span", { class: "quick-icon" }, [icon(iconName)]),
      h("span", { class: "quick-copy" }, [h("strong", {}, title), h("small", {}, text)]),
      h("span", { class: "quick-arrow" }, [icon("ChevronRight", 16)]),
    ]);
  }

  function settingsView() {
    const unread = state.notifications.filter((item) => !item.is_read).length;
    const roleText = displayRoles(state.user).join(", ") || "User";
    const email = state.user?.email || state.user?.login || "No email available";
    const status = state.user?.messenger_status || "offline";
    return page([
      h("section", { class: "settings-grid" }, [
        h("article", { class: "settings-card" }, [
          settingsCardHead("Appearance", "Choose the workspace theme.", "Moon"),
          h("div", { class: "settings-row" }, [
            h("span", {}, [h("strong", {}, state.theme === "dark" ? "Dark mode" : "Light mode"), h("small", {}, "Applies instantly across AnoChat.")]),
            h("button", { class: "settings-toggle", onclick: toggleTheme, "aria-pressed": state.theme === "dark" ? "true" : "false" }, [
              h("span", { class: state.theme === "dark" ? "active" : "" }, [icon("Moon", 15), "Dark"]),
              h("span", { class: state.theme === "light" ? "active" : "" }, [icon("Sun", 15), "Light"]),
            ]),
          ]),
        ]),
        h("article", { class: "settings-card" }, [
          settingsCardHead("Notifications / Status", "Review alerts and update your availability.", "Bell"),
          h("div", { class: "settings-status-grid" }, [
            h("div", { class: "settings-status-tile" }, [
              h("small", {}, "Unread notifications"),
              h("strong", {}, String(unread)),
              h("button", { class: "btn btn-soft compact-btn", onclick: toggleNotifications }, [icon("Bell", 15), state.notificationsOpen ? "Hide alerts" : "View alerts"]),
            ]),
            h("div", { class: "settings-status-tile" }, [
              h("small", {}, "Current status"),
              h("strong", {}, cap(status)),
              presenceControl(),
            ]),
          ]),
          state.notificationsOpen ? notificationPanel() : null,
        ]),
        h("article", { class: "settings-card account-settings-card" }, [
          settingsCardHead("Account", "Your signed-in workspace profile.", "UserRound"),
          h("div", { class: "settings-account" }, [
            h("span", { class: `settings-avatar presence-avatar presence-${status}` }, initials(state.user?.name || "User")),
            h("span", {}, [
              h("strong", {}, state.user?.name || "AnoChat User"),
              h("small", {}, roleText),
              h("small", {}, email),
            ]),
          ]),
          h("button", { class: "btn btn-soft", onclick: () => openModal("profile", state.user) }, [icon("UserRound", 16), "View profile"]),
        ]),
        h("article", { class: "settings-card danger-settings-card" }, [
          settingsCardHead("Logout", "Sign out of this device safely.", "LogOut"),
          h("p", {}, "You will need to sign in again to access this workspace."),
          h("button", { class: "btn btn-danger", onclick: confirmLogout }, [icon("LogOut", 16), "Logout"]),
        ]),
      ]),
    ], "settings-page");
  }

  function settingsCardHead(title, subtitle, iconName) {
    return h("div", { class: "settings-card-head" }, [
      h("span", { class: "settings-card-icon" }, [icon(iconName, 18)]),
      h("span", {}, [h("strong", {}, title), h("small", {}, subtitle)]),
    ]);
  }

  function notificationPanel() {
    const items = state.notifications.slice(0, 6);
    return h("div", { class: "settings-notification-panel" }, [
      h("div", { class: "settings-notification-head" }, [
        h("strong", {}, "Recent notifications"),
        h("button", { class: "link-button", onclick: markNotificationsRead }, "Mark all read"),
      ]),
      items.length ? h("div", { class: "settings-notification-list" }, items.map((item) => h("div", { class: item.is_read ? "notification-item" : "notification-item unread" }, [
        h("span", { class: "notification-icon" }, [icon(notificationIcon(item), 16)]),
        h("span", {}, [h("strong", {}, item.title || "Notification"), h("small", {}, item.body || ""), h("time", {}, formatDate(item.created_at))]),
      ]))) : h("div", { class: "notification-empty" }, [icon("Bell", 20), h("strong", {}, "No notifications"), h("small", {}, "You're all caught up.")]),
    ]);
  }

  function confirmLogout() {
    confirmAction("Logout?", "You will be signed out of this AnoChat workspace.", logout);
  }

  function projectsView() {
    return page([
      h("section", { class: "projects-toolbar card" }, [
        searchBox("Search projects...", "projectSearch"),
        filterSelect("projectStatus", ["all", "active", "completed"], "Status"),
        filterSelect("projectPriority", ["all", "low", "normal", "high", "urgent"], "Priority"),
        canManage() ? h("button", { class: "btn btn-primary projects-new-btn", onclick: () => openModal("project") }, [icon("Plus"), "New Project"]) : null,
      ]),
      h("section", { class: "project-grid" }, filteredProjects().length ? filteredProjects().map(projectCard) : [projectsEmptyState()]),
    ]);
  }

  function projectsEmptyState() {
    return h("article", { class: "projects-empty-state" }, [
      h("div", { class: "empty-illustration" }, [icon("FolderKanban", 32)]),
      h("h2", {}, "No projects match your filters"),
      h("p", {}, "Try adjusting your search or create a new project."),
      canManage() ? h("button", { class: "btn btn-primary", onclick: () => openModal("project") }, [icon("Plus"), "Create your first project"]) : null,
    ]);
  }

  function filteredProjects() {
    const q = state.filters.projectSearch.toLowerCase();
    return state.projects.filter((p) => {
      const matchesSearch = !q || [p.name, p.code, p.status, p.priority, userName(p.manager_id)].join(" ").toLowerCase().indexOf(q) >= 0;
      const matchesStatus = state.filters.projectStatus === "all" || p.status === state.filters.projectStatus;
      const matchesPriority = state.filters.projectPriority === "all" || p.priority === state.filters.projectPriority;
      return matchesSearch && matchesStatus && matchesPriority;
    });
  }

  function projectCards(projects, compact) {
    if (!projects.length && compact) {
      return h("div", { class: "dashboard-empty" }, [
        h("span", {}, [icon("FolderKanban")]),
        h("strong", {}, "No projects yet"),
        h("p", {}, "Create your first project and it will appear here."),
        canManage() ? h("button", { class: "btn btn-primary", onclick: () => openModal("project") }, [icon("Plus"), "Create Project"]) : null,
      ]);
    }
    return projects.length ? h("div", { class: compact ? "dashboard-project-list" : "project-grid" }, projects.map(compact ? dashboardProjectRow : projectCard)) : emptyState("No projects yet.");
  }

  function dashboardProjectRow(project) {
    return h("article", { class: "dashboard-project-row" }, [
      h("span", { class: "project-dot" }),
      h("div", {}, [h("strong", {}, project.name), h("small", {}, project.description || "")]),
      h("div", { class: "badge-row" }, [badge(project.status), badge(project.priority, "priority")]),
      h("small", {}, userName(project.manager_id) || "Unassigned"),
    ]);
  }

  function projectCard(project) {
    return h("article", { class: "project-card" }, [
      h("div", { class: "project-top" }, [
        h("div", {}, [h("h3", {}, project.name), h("p", {}, project.description || "")]),
        h("div", { class: "badge-row" }, [badge(project.status), badge(project.priority, "priority")]),
      ]),
      h("div", { class: "project-meta" }, [
        metaItem("Manager", userName(project.manager_id) || "Unassigned"),
        metaItem("Customer", projectCustomerNames(project)),
        metaItem("Deadline", project.deadline || "No deadline"),
        metaItem("Assigned", `${(project.members || []).length} users`),
      ]),
      h("div", { class: "progress-track" }, h("span", { style: `width:${Math.max(0, Math.min(100, project.completion_rate || 0))}%` })),
      h("div", { class: "card-actions" }, [
        canManage() ? h("button", { class: "btn btn-soft", onclick: () => openModal("project", project) }, [icon("Edit"), "Edit"]) : null,
        canManage() ? h("button", { class: "btn btn-danger", onclick: () => confirmAction("Delete project?", "This will permanently remove the project record.", () => deleteProject(project.id)) }, [icon("Trash"), "Delete"]) : null,
      ]),
    ]);
  }

  function chattersView() {
    const active = state.chatters.find((item) => sameId(item.id, state.activeChatter));
    const showInfo = !!active && state.chatterInfoOpen;
    return page([
      h("section", { class: showInfo ? "chat-shell info-open" : "chat-shell" }, [
        h("aside", { class: "conversation-panel card" }, [
          h("div", { class: "panel-title chat-panel-title" }, [
            h("div", {}, [h("h2", {}, "Conversations"), h("p", { class: "muted" }, "Project and team chatters")]),
          ]),
          searchBox("Search conversations...", "chatterSearch"),
          chatterList(),
        ]),
        h("article", { class: "chat-window card" }, [
          h("div", { class: "chat-head" }, [
            active ? chatHeaderIdentity(active) : h("div", { class: "chat-header-identity" }, [h("span", { class: "chat-header-avatar" }, [icon("MessagesSquare", 22)]), h("span", {}, [h("h2", {}, "Messages"), h("p", { class: "muted" }, "Select a conversation")])]),
            active ? chatHeaderActions(active) : null,
          ]),
          h("div", { class: "message-stream" }, active ? (state.messages.length ? messageTimeline(state.messages) : [chatEmptyState()]) : [chatEmptyState("Select a conversation", "Choose a chatter from the list to view messages.")]),
          active ? typingIndicator() : null,
          active ? messageComposer() : null,
        ]),
        showInfo ? chatterInfoPanel(active) : null,
      ]),
    ], "chat-page");
  }

  function chatterList(limit, openOnClick) {
    const rows = filteredChatters(limit);
    return rows.length ? h("div", { class: "conversation-list" }, rows.map((c) => h("button", {
      class: sameId(c.id, state.activeChatter) ? "conversation active" : "conversation",
      "aria-current": sameId(c.id, state.activeChatter) ? "true" : null,
      onclick: () => openOnClick ? openChatter(c.id) : selectChatter(c.id),
    }, [
      h("span", { class: "conversation-avatar" }, [h("i", { class: "online-dot" }), initials(c.name)]),
      h("span", { class: "conversation-copy" }, [h("strong", {}, c.name), h("small", {}, c.last_message_preview || "No messages yet")]),
      h("span", { class: "conversation-meta" }, [h("small", {}, projectName(c.project_id) || "General"), memberAvatars(c)]),
    ]))) : h("div", { class: "chat-empty-compact" }, [h("span", {}, [icon("MessagesSquare")]), h("strong", {}, "No conversations"), h("p", {}, "Try another search or create a chatter.")]);
  }

  function filteredChatters(limit) {
    const q = state.filters.chatterSearch.toLowerCase();
    const rows = state.chatters.filter((c) => !q || [c.name, c.last_message_preview, projectName(c.project_id)].join(" ").toLowerCase().indexOf(q) >= 0);
    return limit ? rows.slice(0, limit) : rows;
  }

  function chatHeaderIdentity(active) {
    return h("button", { type: "button", class: "chat-header-identity chat-info-trigger", onclick: () => toggleChatterInfo(active) }, [
      h("span", { class: "chat-header-avatar" }, initials(active.name)),
      h("span", { class: "chat-header-copy" }, [
        h("span", { class: "chat-title-row" }, [h("h2", {}, active.name), badge(projectName(active.project_id) || "General chatter", "chat-type")]),
        memberAvatars(active),
      ]),
    ]);
  }

  function chatHeaderActions(active) {
    return h("div", { class: "chat-head-actions" }, [
      h("button", { type: "button", title: "Search", "aria-label": "Search messages" }, [icon("Search", 19)]),
      h("button", { type: "button", title: "More", "aria-label": "More" }, [icon("MoreVertical", 18)]),
    ]);
  }

  function chatterMemberText(chatter) {
    const count = chatter.members?.length || chatter.member_ids?.length || 0;
    return count ? `${count} member${count === 1 ? "" : "s"}` : "No members yet";
  }

  function memberAvatars(chatter) {
    const members = chatter.members || [];
    if (!members.length) return h("span", { class: "member-avatar-empty", title: "No members yet" }, "No members");
    const visible = members.slice(0, 3);
    const extra = members.length - visible.length;
    const avatars = visible.map((member) => h("span", { class: "member-mini-avatar", title: member.name || member.email || "Member" }, initials(member.name || member.email)));
    if (extra > 0) avatars.push(h("span", { class: "member-mini-avatar extra", title: `${extra} more member${extra === 1 ? "" : "s"}` }, `+${extra}`));
    return h("span", { class: "member-avatar-stack", title: chatterMemberText(chatter) }, avatars);
  }

  function chatterInfoPanel(chatter) {
    const members = chatter.members || [];
    const files = sharedChatterFiles(chatter);
    const images = files.filter((file) => String(file.content_type || "").startsWith("image/"));
    const documents = files.filter((file) => !String(file.content_type || "").startsWith("image/"));
    const memberLimit = 4;
    const imageLimit = 4;
    const documentLimit = 4;
    const visibleMembers = state.chatInfoExpanded.members ? members : members.slice(0, memberLimit);
    const visibleImages = state.chatInfoExpanded.images ? images : images.slice(0, imageLimit);
    const visibleDocuments = state.chatInfoExpanded.documents ? documents : documents.slice(0, documentLimit);
    return h("aside", { class: "conversation-details-card chat-info-panel" }, [
      h("button", { type: "button", class: "chat-info-close", title: "Hide details", onclick: () => { state.chatterInfoOpen = false; render(); } }, [icon("X", 16)]),
      h("div", { class: "conversation-details-head" }, [
        h("span", { class: "conversation-details-avatar" }, initials(chatter.name)),
        h("span", {}, [
          h("strong", {}, chatter.name),
          h("small", {}, `${members.length} member${members.length === 1 ? "" : "s"}`),
        ]),
      ]),
      h("p", { class: "conversation-details-desc" }, chatter.description || "No description added."),
      h("div", { class: "conversation-info-list" }, [
        h("div", {}, [icon("FolderKanban", 14), h("span", {}, projectName(chatter.project_id) || "General chatter")]),
        h("div", {}, [icon("Calendar", 14), h("span", {}, `Created ${formatDate(chatter.created_at)}`)]),
        h("div", {}, [icon("Paperclip", 14), h("span", {}, `${files.length} shared file${files.length === 1 ? "" : "s"}`)]),
      ]),
      canManage() ? chatterInfoActions(chatter) : null,
      chatInfoSectionTitle("Users", "Members", members.length, "members", memberLimit),
      members.length ? h("div", { class: "conversation-details-members" }, visibleMembers.map((member) => h("div", { class: "conversation-detail-member" }, [
        h("span", { class: "member-mini-avatar" }, initials(member.name || member.email)),
        h("span", {}, [h("strong", {}, member.name || member.email), h("small", {}, displayRoles(member).join(", ") || "Member")]),
      ]))) : h("div", { class: "conversation-details-empty" }, "No members assigned."),
      chatInfoSectionTitle("Image", "Shared photos/screenshots", images.length, "images", imageLimit),
      images.length ? h("div", { class: "chat-info-media-grid" }, visibleImages.map((file) => h("button", { type: "button", onclick: () => openImagePreview(file) }, [
        imagePreview(file, "chat-info-image"),
        h("span", {}, file.filename || "Image"),
      ]))) : h("div", { class: "conversation-details-empty" }, "No shared images."),
      chatInfoSectionTitle("Paperclip", "Shared documents/files", documents.length, "documents", documentLimit),
      documents.length ? h("div", { class: "conversation-details-files" }, visibleDocuments.map((file) => h("button", { type: "button", onclick: () => downloadAttachment(file) }, [
        fileTypeBadge(file),
        h("span", {}, [h("strong", {}, file.filename || "Attachment"), h("small", {}, prettyBytes(file.size_bytes || 0))]),
      ]))) : h("div", { class: "conversation-details-empty" }, "No shared files yet."),
    ]);
  }

  function chatInfoSectionTitle(iconName, label, count, key, limit) {
    const expanded = !!state.chatInfoExpanded[key];
    const canToggle = count > limit;
    return h("div", { class: "chat-info-section-title" }, [
      h("span", { class: "chat-info-title-main" }, [icon(iconName, 14), h("span", {}, label)]),
      h("span", { class: "chat-info-title-count" }, String(count)),
      canToggle ? h("button", {
        type: "button",
        class: "chat-info-see-all",
        onclick: () => {
          state.chatInfoExpanded = { ...state.chatInfoExpanded, [key]: !expanded };
          render();
        },
      }, expanded ? "Show less" : "See all") : null,
    ]);
  }

  function chatterInfoActions(chatter) {
    return h("div", { class: "chat-info-actions", "aria-label": "Chatter actions" }, [
      h("button", { type: "button", class: "chat-info-action edit", onclick: () => openModal("chatter", chatter) }, [icon("Edit", 14), h("span", {}, "Edit")]),
      canDeleteChatter(chatter) ? h("button", { type: "button", class: "chat-info-action danger", onclick: () => confirmAction("Delete chatter?", "This hides the chatter from the active list.", () => deleteChatter(chatter.id)) }, [icon("Trash", 14), h("span", {}, "Delete")]) : null,
    ]);
  }

  function chatEmptyState(title, subtitle) {
    return h("div", { class: "chat-empty-state" }, [
      h("span", { class: "empty-illustration" }, [icon("MessagesSquare", 34)]),
      h("h2", {}, title || "No messages yet"),
      h("p", {}, subtitle || "Start the conversation by sending a message."),
    ]);
  }

  function typingIndicator() {
    const users = state.typingUsers || [];
    if (!users.length) return h("div", { class: "typing-indicator empty", "aria-live": "polite" });
    const names = users.map((user) => user.name || `User ${user.id}`);
    const text = names.length === 1 ? `${names[0]} is typing...` : `${names.slice(0, 2).join(", ")}${names.length > 2 ? ` +${names.length - 2}` : ""} are typing...`;
    return h("div", { class: "typing-indicator", "aria-live": "polite" }, [
      h("span", { class: "typing-dots" }, [h("i"), h("i"), h("i")]),
      h("span", {}, text),
    ]);
  }

  function messageTimeline(messages) {
    const nodes = [];
    let lastDay = "";
    (messages || []).forEach((message) => {
      const dayKey = messageDayKey(message.created_at);
      if (dayKey && dayKey !== lastDay) {
        lastDay = dayKey;
        nodes.push(dateDivider(message.created_at));
      }
      nodes.push(messageBubble(message));
    });
    return nodes;
  }

  function dateDivider(value) {
    return h("div", { class: "message-date-divider" }, [
      h("span"),
      h("time", {}, formatMessageDay(value)),
      h("span"),
    ]);
  }

  function messageBubble(message) {
    const own = sameId(message.sender_id, state.user.id);
    const editing = state.editingMessage && Number(state.editingMessage.id) === Number(message.id);
    const editable = canEditMessage(message);
    const deletedByCurrentUser = Number(message.deleted_by_id) === Number(state.user?.id);
    const hasAttachments = !!(message.attachments && message.attachments.length);
    const hasAudio = hasAttachments && message.attachments.some(isAudioFile);
    const defaultAttachmentBody = hasAttachments && ["Attachment", "Voice note"].includes(String(message.body || "").trim());
    const bodyText = defaultAttachmentBody ? "" : (message.body || "");
    const deletedNote = message.is_deleted && isAdmin()
      ? `This message was deleted by ${deletedByCurrentUser ? "you" : (message.deleted_by_name || userName(message.deleted_by_id) || "a user")}.`
      : "";
    const authorName = own ? "You" : (userName(message.sender_id) || "Member");
    const stamp = `${formatMessageTime(message.created_at)}${message.is_edited ? " · edited" : ""}`;
    return h("div", { class: own ? "message-row own" : "message-row", id: `message-${message.id}` }, [
      !own ? h("span", { class: "message-avatar" }, initials(authorName)) : null,
      h("div", { class: "message-stack" }, [
        h("div", { class: `${message.is_deleted ? "bubble deleted-message" : "bubble"}${hasAttachments ? " attachment-bubble" : ""}${hasAudio ? " voice-bubble" : ""}` }, [
          h("div", { class: "bubble-meta" }, [
            h("strong", {}, authorName),
            h("span", { class: "message-actions" }, [
              messageMenu(message, editable, own),
            ]),
          ]),
          message.reply_to_id ? replyPreview(message) : null,
          editing ? editMessageForm(message) : (bodyText ? h("p", {}, bodyText) : null),
          hasAttachments ? h("div", { class: "attachment-strip" }, message.attachments.map(messageAttachment)) : null,
          h("div", { class: "bubble-footer" }, [
            h("time", {}, stamp),
          ]),
        ]),
        deletedNote ? h("small", { class: "deleted-message-note" }, [icon("Trash", 12), h("span", {}, deletedNote)]) : null,
      ]),
      own ? h("span", { class: "message-avatar own-avatar" }, initials(state.user?.name || "You")) : null,
    ]);
  }

  function messageMenu(message, editable, own) {
    if (message.is_deleted) return null;
    const canReply = !activeChatterIsReadOnly();
    const canDelete = !activeChatterIsReadOnly() && (own || isAdmin());
    if (!canReply && !editable && !canDelete) return null;
    const open = Number(state.openMessageMenu) === Number(message.id);
    return h("span", { class: "message-menu-wrap" }, [
      h("button", {
        type: "button",
        class: "message-menu-trigger",
        title: "Message options",
        "aria-label": "Message options",
        onclick: (event) => {
          event.preventDefault();
          event.stopPropagation();
          state.openMessageMenu = open ? null : message.id;
          render();
        },
      }, [icon("MoreVertical", 16)]),
      open ? h("span", { class: "message-options-menu" }, [
        h("button", { type: "button", onclick: () => { state.openMessageMenu = null; openMessageInfo(message); } }, [icon("Eye", 14), h("span", {}, "Info")]),
        canReply ? h("button", { type: "button", onclick: () => { state.openMessageMenu = null; startReply(message); } }, [icon("MessageCircle", 14), h("span", {}, "Reply")]) : null,
        editable ? h("button", { type: "button", onclick: () => { state.openMessageMenu = null; startEditMessage(message); } }, [icon("Edit", 14), h("span", {}, "Edit")]) : null,
        canDelete ? h("button", { type: "button", class: "danger", onclick: () => { state.openMessageMenu = null; confirmAction("Delete message?", "This message will be removed.", () => deleteMessage(message.id)); } }, [icon("Trash", 14), h("span", {}, "Delete")]) : null,
      ]) : null,
    ]);
  }

  function canEditMessage(message) {
    if (!message || message.is_deleted || activeChatterIsReadOnly()) return false;
    if (Number(message.sender_id) !== Number(state.user?.id)) return false;
    if (!message.can_edit) return false;
    if (!message.can_edit_until) return true;
    return new Date(message.can_edit_until).getTime() > Date.now();
  }

  function editMessageForm(message) {
    return h("form", { class: "message-edit-form", onsubmit: (event) => saveEditedMessage(event, message) }, [
      h("textarea", { name: "body", rows: "3", oninput: (event) => { state.editingBody = event.target.value; } }, state.editingBody),
      h("div", { class: "message-edit-actions" }, [
        h("button", { type: "button", class: "icon-btn", title: "Cancel edit", "aria-label": "Cancel edit", onclick: cancelEditMessage }, [icon("X", 14)]),
        h("button", { type: "submit", class: "btn btn-primary compact-btn", title: "Save edit" }, [icon("Check", 14), "Save"]),
      ]),
    ]);
  }

  function replyPreview(message) {
    return h("button", { type: "button", class: "reply-preview", onclick: () => scrollToMessage(message.reply_to_id), title: "Referenced message" }, [
      h("strong", {}, message.reply_to_sender_name || userName(message.reply_to_sender_id) || "Message"),
      h("span", {}, message.reply_to_body || "Attachment"),
    ]);
  }

  function messageSeenViewers(message) {
    const seen = Array.isArray(message.seen_by) ? message.seen_by : [];
    const seenIds = new Set();
    return seen.filter((user) => {
      const id = Number(user?.id);
      if (!id || id === Number(state.user?.id) || id === Number(message.sender_id) || seenIds.has(id)) return false;
      seenIds.add(id);
      return true;
    });
  }

  function openMessageInfo(message) {
    state.modal = { type: "messageInfo", message };
    render();
  }

  function startReply(message) {
    if (activeChatterIsReadOnly()) {
      toast("This chatter is read-only for your account.", "error");
      render();
      return;
    }
    state.replyTo = message;
    state.openMessageMenu = null;
    render();
    window.setTimeout(() => {
      const input = document.querySelector(".composer input[name='body']");
      if (input) input.focus();
    }, 0);
  }

  function clearReply() {
    state.replyTo = null;
    render();
  }

  function startEditMessage(message) {
    if (!canEditMessage(message)) {
      toast("Message edit window has expired.", "error");
      render();
      return;
    }
    state.replyTo = null;
    state.editingMessage = message;
    state.editingBody = message.body || "";
    state.openMessageMenu = null;
    render();
    window.setTimeout(() => {
      const input = document.querySelector(".message-edit-form textarea");
      if (input) input.focus();
    }, 0);
  }

  function cancelEditMessage() {
    state.editingMessage = null;
    state.editingBody = "";
    render();
  }

  function replySnippet(message) {
    if (!message) return "";
    const text = String(message.body || "").trim();
    const fallback = message.attachments && message.attachments.length ? "Attachment" : "Message";
    return (text || fallback).slice(0, 140);
  }

  function scrollToMessage(id) {
    if (!id) return;
    const target = document.getElementById(`message-${id}`);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("message-row-highlight");
    window.setTimeout(() => target.classList.remove("message-row-highlight"), 1100);
  }

  function messageComposer() {
    const active = state.chatters.find((item) => sameId(item.id, state.activeChatter));
    if (chatterIsReadOnly(active)) {
      return h("div", { class: "composer read-only-composer" }, [
        h("span", { class: "read-only-lock" }, [icon("Lock", 16)]),
        h("span", {}, [
          h("strong", {}, "Read-only chatter"),
          h("small", {}, "You can view this conversation, but you cannot send messages or upload files here."),
        ]),
      ]);
    }
    return h("form", { class: "composer", onsubmit: sendMessage }, [
      state.replyTo ? replyComposerPreview() : null,
      state.voiceRecording ? voiceRecordingBar() : null,
      state.pendingVoicePreviewUrl ? pendingVoicePreview() : null,
      h("div", { class: "composer-bar mention-anchor" }, [
        h("label", { class: "file-chip chat-file-chip", title: "Attach file", "aria-label": "Attach file" }, [icon("Paperclip"), h("span", { class: "file-chip-text" }, state.pendingAttachment?.name || "Attach"), h("input", { type: "file", name: "file", onchange: updateAttachmentLabel })]),
        h("div", { class: "composer-input-wrap" }, [
          h("input", { name: "body", value: state.composerBody, placeholder: "Your message", autocomplete: "off", oninput: updateComposerText, onkeydown: handleComposerKeydown }),
        ]),
        state.mention.open ? mentionDropdown(active) : null,
        voiceButton(active),
        h("button", { class: "btn btn-primary chat-send-btn", disabled: state.sendingMessage, title: "Send message", "aria-label": "Send message" }, [icon("Send"), h("span", {}, state.sendingMessage ? "Sending..." : "Send")]),
      ]),
    ]);
  }

  function messageAttachment(file) {
    if (isAudioFile(file)) return audioAttachment(file);
    if (isImageFile(file)) {
      return h("button", { type: "button", class: "message-image-tile", title: file.filename || "Image", onclick: () => openImagePreview(file) }, [
        imagePreview(file, "message-image-preview"),
      ]);
    }
    return h("button", { type: "button", class: "message-file-card", title: file.filename || "Attachment", onclick: () => downloadAttachment(file) }, [
      fileTypeBadge(file),
      h("span", { class: "message-file-meta" }, [
        h("strong", {}, file.filename || "Attachment"),
        h("small", {}, prettyBytes(file.size_bytes || 0)),
      ]),
    ]);
  }

  function audioAttachment(file) {
    const src = state.audioPreviews[file.id];
    const key = `attachment-${file.id}`;
    const audioState = voiceAudioState(file);
    const playing = !!audioState.isPlaying;
    const progress = voiceProgress(file);
    const duration = audioState.duration || file.duration_seconds || 0;
    return h("div", { class: "voice-note-card", "data-file-id": file.id }, [
      h("button", {
        type: "button",
        class: playing ? "voice-play-btn playing" : "voice-play-btn",
        title: playing ? "Pause voice note" : "Play voice note",
        "aria-label": playing ? "Pause voice note" : "Play voice note",
        onclick: () => toggleVoicePlayback(file),
      }, [icon(playing ? "Pause" : "Play", 18)]),
      h("span", { class: "voice-waveform", "aria-hidden": "true" }, waveformBars(progress)),
      h("small", { class: "voice-duration" }, formatDuration(playing && audioState.currentTime ? audioState.currentTime : duration)),
      src ? h("audio", {
        preload: "metadata",
        src,
        "data-audio-key": key,
        onplay: (event) => updateAudioState(file.id, event.currentTarget),
        onpause: (event) => updateAudioState(file.id, event.currentTarget),
        ontimeupdate: (event) => updateAudioState(file.id, event.currentTarget, { throttle: true }),
        onended: (event) => updateAudioState(file.id, event.currentTarget, { ended: true }),
        onloadedmetadata: (event) => updateAudioState(file.id, event.currentTarget),
      }) : h("button", { type: "button", class: "voice-load-btn", onclick: () => loadAudioPreview(file) }, state.loadingAudio.has(file.id) ? "Loading..." : "Load playback"),
    ]);
  }

  function waveformBars(progress) {
    const bars = [14, 22, 11, 28, 18, 34, 24, 13, 30, 20, 16, 26, 12, 23, 18, 30, 14, 22, 10, 18];
    const played = Math.round(Math.max(0, Math.min(1, progress || 0)) * bars.length);
    return bars.map((height, index) => h("i", { class: index < played ? "played" : "", style: `height:${height}px` }));
  }

  async function toggleVoicePlayback(file) {
    if (!file) return;
    if (!state.audioPreviews[file.id]) {
      await loadAudioPreview(file);
    }
    let audio = await findVoiceAudioElement(file);
    if (!audio && state.audioPreviews[file.id] && !isAudioPlaying()) {
      render();
      audio = await findVoiceAudioElement(file);
    }
    if (!audio) return;
    document.querySelectorAll("audio[data-audio-key]").forEach((item) => {
      if (item !== audio) item.pause();
    });
    if (audio.paused) {
      if (audio.ended) audio.currentTime = 0;
      audio.play().catch(() => toast("Could not play voice note.", "error"));
    } else {
      audio.pause();
    }
  }

  function voiceAudioState(file) {
    return state.audioState[file?.id] || {
      currentTime: 0,
      duration: Number(file?.duration_seconds) || 0,
      isPlaying: false,
    };
  }

  function voiceProgress(file) {
    const item = voiceAudioState(file);
    const duration = Number(item.duration) || Number(file?.duration_seconds) || 0;
    if (!duration) return 0;
    return Math.max(0, Math.min(1, (Number(item.currentTime) || 0) / duration));
  }

  function updateAudioState(fileId, audio, options = {}) {
    if (!fileId || !audio) return;
    const previous = state.audioState[fileId] || {};
    const ended = options.ended || audio.ended;
    const currentTime = ended ? 0 : (Number(audio.currentTime) || 0);
    const duration = Number(audio.duration) || previous.duration || 0;
    const isPlaying = !ended && !audio.paused;
    if (options.throttle && Math.abs((previous.currentTime || 0) - currentTime) < 0.18 && previous.isPlaying === isPlaying) return;
    const next = { currentTime, duration, isPlaying };
    state.audioState = { ...state.audioState, [fileId]: next };
    updateVoiceCardDom(fileId, next);
  }

  function updateVoiceCardDom(fileId, item) {
    const card = document.querySelector(`.voice-note-card[data-file-id="${fileId}"]`);
    if (!card) return;
    const duration = Number(item.duration) || 0;
    const progress = duration ? Math.max(0, Math.min(1, (Number(item.currentTime) || 0) / duration)) : 0;
    const bars = Array.from(card.querySelectorAll(".voice-waveform i"));
    const played = Math.round(progress * bars.length);
    bars.forEach((bar, index) => bar.classList.toggle("played", index < played));
    const durationNode = card.querySelector(".voice-duration");
    if (durationNode) durationNode.textContent = formatDuration(item.isPlaying && item.currentTime ? item.currentTime : duration);
    const playButton = card.querySelector(".voice-play-btn");
    if (playButton) {
      playButton.classList.toggle("playing", !!item.isPlaying);
      playButton.title = item.isPlaying ? "Pause voice note" : "Play voice note";
      playButton.setAttribute("aria-label", item.isPlaying ? "Pause voice note" : "Play voice note");
      playButton.replaceChildren(icon(item.isPlaying ? "Pause" : "Play", 18));
    }
  }

  function nextFrame() {
    return new Promise((resolve) => window.requestAnimationFrame(resolve));
  }

  async function findVoiceAudioElement(file) {
    const key = `attachment-${file.id}`;
    let audio = document.querySelector(`audio[data-audio-key="${key}"]`);
    if (audio) return audio;
    await nextFrame();
    audio = document.querySelector(`audio[data-audio-key="${key}"]`);
    if (audio) return audio;
    await nextFrame();
    return document.querySelector(`audio[data-audio-key="${key}"]`);
  }

  function voiceButton(active) {
    const unsupported = !voiceRecorderSupported();
    const disabled = unsupported || !active?.allow_voice_notes || state.sendingMessage || !!state.pendingAttachment;
    const recording = !!state.voiceRecording;
    return h("button", {
      type: "button",
      class: recording ? "voice-btn recording" : "voice-btn",
      title: unsupported ? "Voice recording is not supported in this browser" : (recording ? "Stop recording" : "Record voice note"),
      "aria-label": recording ? "Stop recording" : "Record voice note",
      disabled,
      onclick: recording ? stopVoiceRecording : startVoiceRecording,
    }, [icon(recording ? "Square" : "Mic"), h("span", {}, recording ? formatDuration(recordingDuration()) : "Voice")]);
  }

  function voiceRecordingBar() {
    return h("div", { class: "voice-recording-bar" }, [
      h("span", { class: "recording-dot" }),
      h("span", {}, `Recording ${formatDuration(recordingDuration())}`),
      h("button", { type: "button", title: "Cancel recording", "aria-label": "Cancel recording", onclick: () => cancelVoiceRecording(false) }, [icon("X", 14)]),
    ]);
  }

  function pendingVoicePreview() {
    return h("div", { class: "pending-voice-preview" }, [
      h("span", { class: "voice-note-icon" }, [icon("Mic", 16)]),
      h("div", { class: "voice-note-body" }, [
        h("strong", {}, "Review voice note"),
        h("small", {}, `${formatDuration(state.pendingVoiceDuration)} recorded`),
        h("audio", { controls: true, preload: "metadata", src: state.pendingVoicePreviewUrl, "data-audio-key": "pending-voice" }),
      ]),
      h("button", { type: "button", class: "pending-voice-remove", title: "Discard voice note", "aria-label": "Discard voice note", onclick: () => clearPendingVoiceNote(true) }, [icon("X", 14)]),
    ]);
  }

  function openImagePreview(file) {
    state.modal = { type: "imagePreview", file };
    render();
  }

  function replyComposerPreview() {
    const message = state.replyTo;
    return h("div", { class: "composer-reply-preview" }, [
      h("span", {}, [
        h("strong", {}, `Replying to ${userName(message.sender_id) || "message"}`),
        h("small", {}, replySnippet(message)),
      ]),
      h("button", { type: "button", title: "Cancel reply", "aria-label": "Cancel reply", onclick: clearReply }, [icon("X", 14)]),
    ]);
  }

  function imagePreview(file, className) {
    const src = state.attachmentPreviews[file.id];
    return src
      ? h("img", { class: className || "image-preview", src, alt: file.filename || "Attachment image", loading: "lazy" })
      : h("span", { class: `${className || "image-preview"} image-preview-loading` }, [icon("Image", 18)]);
  }

  function isImageFile(file) {
    return String(file?.content_type || "").startsWith("image/");
  }

  function isAudioFile(file) {
    return String(file?.content_type || "").startsWith("audio/");
  }

  function fileExtension(file) {
    const filename = String(file?.filename || "").toLowerCase();
    const extension = filename.includes(".") ? filename.split(".").pop() : "";
    if (extension) return extension;
    const type = String(file?.content_type || "").toLowerCase();
    if (type.includes("pdf")) return "pdf";
    if (type.includes("word")) return "docx";
    if (type.includes("excel") || type.includes("spreadsheet")) return "xlsx";
    if (type.includes("powerpoint") || type.includes("presentation")) return "pptx";
    if (type.includes("zip")) return "zip";
    if (type.includes("json")) return "json";
    if (type.includes("csv")) return "csv";
    if (type.startsWith("text/")) return "txt";
    return "file";
  }

  function fileBadgeLabel(file) {
    const extension = fileExtension(file);
    const aliases = { jpeg: "JPG", jpg: "JPG", xlsx: "XLS", xls: "XLS", doc: "DOC", docx: "DOCX", ppt: "PPT", pptx: "PPT" };
    return aliases[extension] || extension.slice(0, 4).toUpperCase();
  }

  function fileTypeBadge(file) {
    const extension = fileExtension(file);
    return h("span", { class: `file-type-badge ${extension}` }, [
      h("span", { class: "file-type-corner" }),
      h("strong", {}, fileBadgeLabel(file)),
    ]);
  }

  function formatDuration(seconds) {
    const total = Math.max(0, Math.round(Number(seconds) || 0));
    const minutes = Math.floor(total / 60);
    const rest = String(total % 60).padStart(2, "0");
    return `${minutes}:${rest}`;
  }

  function recordingDuration() {
    return state.voiceRecording ? (Date.now() - state.voiceRecording.startedAt) / 1000 : 0;
  }

  function voiceRecorderSupported() {
    return !!(navigator.mediaDevices?.getUserMedia && (window.AudioContext || window.webkitAudioContext));
  }

  async function startVoiceRecording() {
    if (!voiceRecorderSupported()) {
      toast("Voice recording is not supported in this browser.", "error");
      return;
    }
    if (state.pendingAttachment) {
      toast("Send or remove the current attachment before recording.", "error");
      return;
    }
    const active = state.chatters.find((item) => Number(item.id) === Number(state.activeChatter));
    if (!active?.allow_voice_notes) {
      toast("Voice notes are disabled for this chatter.", "error");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      const chunks = [];
      processor.onaudioprocess = (event) => {
        chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
        event.outputBuffer.getChannelData(0).fill(0);
      };
      source.connect(processor);
      processor.connect(audioContext.destination);
      state.voiceRecording = {
        stream,
        audioContext,
        source,
        processor,
        chunks,
        sampleRate: audioContext.sampleRate,
        startedAt: Date.now(),
        timer: window.setInterval(render, 1000),
      };
      render();
    } catch (err) {
      toast("Microphone permission is needed to record voice notes.", "error");
    }
  }

  function stopVoiceRecording() {
    const recording = state.voiceRecording;
    if (!recording) return;
    finishVoiceRecording(recording);
  }

  function cancelVoiceRecording(silent) {
    const recording = state.voiceRecording;
    if (!recording) return;
    state.voiceRecording = null;
    cleanupVoiceRecording(recording);
    if (!silent) toast("Voice note discarded.", "success");
    render();
  }

  function clearPendingVoiceNote(showToast, skipRender) {
    if (state.pendingVoicePreviewUrl) URL.revokeObjectURL(state.pendingVoicePreviewUrl);
    const hadVoiceNote = !!state.pendingVoiceDuration || !!state.pendingVoicePreviewUrl;
    state.pendingAttachment = null;
    state.pendingVoiceDuration = null;
    state.pendingVoicePreviewUrl = null;
    if (state.composerBody === "Voice note") state.composerBody = "";
    if (showToast && hadVoiceNote) toast("Voice note discarded.", "success");
    if (!skipRender) render();
  }

  function cleanupVoiceRecording(recording) {
    if (!recording) return;
    if (recording.timer) window.clearInterval(recording.timer);
    try { recording.processor?.disconnect(); } catch (_) {}
    try { recording.source?.disconnect(); } catch (_) {}
    recording.stream?.getTracks().forEach((track) => track.stop());
    if (recording.audioContext?.state !== "closed") recording.audioContext?.close?.();
  }

  function finishVoiceRecording(recording) {
    if (!recording || state.voiceRecording !== recording) return;
    const duration = recordingDuration();
    state.voiceRecording = null;
    cleanupVoiceRecording(recording);
    if (!recording.chunks.length || duration < 1) {
      toast("Voice note was too short.", "error");
      render();
      return;
    }
    const blob = encodeWav(flattenAudioChunks(recording.chunks), recording.sampleRate);
    if (state.pendingVoicePreviewUrl) URL.revokeObjectURL(state.pendingVoicePreviewUrl);
    state.pendingAttachment = new File([blob], "voice-note.wav", { type: "audio/wav" });
    state.pendingVoiceDuration = duration;
    state.pendingVoicePreviewUrl = URL.createObjectURL(blob);
    state.composerBody = state.composerBody || "Voice note";
    toast("Voice note ready. Listen before sending.", "success");
    render();
  }

  function flattenAudioChunks(chunks) {
    const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
    const samples = new Float32Array(length);
    let offset = 0;
    chunks.forEach((chunk) => {
      samples.set(chunk, offset);
      offset += chunk.length;
    });
    return samples;
  }

  function encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    writeAscii(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeAscii(view, 8, "WAVE");
    writeAscii(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeAscii(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);
    let offset = 44;
    for (let i = 0; i < samples.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
    return new Blob([view], { type: "audio/wav" });
  }

  function writeAscii(view, offset, text) {
    for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
  }

  async function ensureVisibleImagePreviews() {
    const files = []
      .concat(state.messages.flatMap((message) => message.attachments || []))
      .concat(state.files || [])
      .concat(state.modal?.type === "imagePreview" && state.modal.file ? [state.modal.file] : []);
    const unique = new Map(files.filter(isImageFile).map((file) => [file.id, file]));
    unique.forEach(async (file) => {
      if (Object.prototype.hasOwnProperty.call(state.attachmentPreviews, file.id) || state.loadingPreviews.has(file.id)) return;
      state.loadingPreviews.add(file.id);
      try {
        const blob = await apiClient.get(`/api/attachments/${file.id}`);
        state.attachmentPreviews[file.id] = URL.createObjectURL(blob);
        render();
      } catch (_) {
        state.attachmentPreviews[file.id] = "";
      } finally {
        state.loadingPreviews.delete(file.id);
      }
    });
  }

  async function loadAudioPreview(file, options = {}) {
    if (!file || state.loadingAudio.has(file.id)) return;
    if (state.audioPreviews[file.id]) {
      if (!options.silent && !isAudioPlaying()) render();
      return;
    }
    state.loadingAudio.add(file.id);
    if (!options.silent && !isAudioPlaying()) render();
    try {
      const blob = await apiClient.get(`/api/attachments/${file.id}`);
      state.audioPreviews[file.id] = URL.createObjectURL(blob);
    } catch (err) {
      toast(err.message || "Could not load voice note.", "error");
    } finally {
      state.loadingAudio.delete(file.id);
      if (!options.silent && !isAudioPlaying()) render();
    }
  }

  async function ensureVisibleAudioPreviews() {
    const files = state.messages.flatMap((message) => message.attachments || []).filter(isAudioFile);
    files.slice(-20).forEach((file) => loadAudioPreview(file, { silent: true }));
  }

  function mentionDropdown(chatter) {
    const options = mentionOptions(chatter);
    return h("div", { class: "mention-menu" }, options.length ? options.map((option) => h("button", { type: "button", onclick: () => insertMention(option.value) }, [
      h("span", { class: option.everyone ? "mention-avatar everyone" : "mention-avatar" }, option.everyone ? "@" : initials(option.name)),
      h("span", {}, [h("strong", {}, option.label), h("small", {}, option.role || "Workspace member")]),
    ])) : [h("div", { class: "mention-empty" }, "No members found")]);
  }

  function mentionOptions(chatter) {
    const query = String(state.mention.query || "").toLowerCase();
    const everyone = { everyone: true, value: "everyone", name: "everyone", label: "@everyone", role: "Notify all members" };
    const members = (chatter?.members || []).map((member) => ({
      value: safeMentionName(member.name || member.email || `user${member.id}`),
      name: member.name || member.email || "Member",
      label: `@${member.name || member.email || "Member"}`,
      role: displayRoles(member).join(", ") || "Member",
    }));
    return [everyone].concat(members).filter((item) => {
      if (!query) return true;
      return [item.value, item.name, item.label, item.role].join(" ").toLowerCase().indexOf(query) >= 0;
    }).slice(0, 8);
  }

  function safeMentionName(name) {
    return String(name || "member").trim().replace(/^@+/, "").replace(/\s+/g, "");
  }

  function currentMentionToken(text) {
    const match = String(text || "").match(/(^|\s)@([A-Za-z0-9_.-]*)$/);
    return match ? match[2] : null;
  }

  function updateComposerText(event) {
    const body = event.target.value;
    const query = currentMentionToken(body);
    const nextOpen = query !== null;
    const menuChanged = state.mention.open !== nextOpen || state.mention.query !== (query || "");
    state.composerBody = body;
    state.mention = { open: nextOpen, query: query || "" };
    syncTypingState(body.trim().length > 0);
    if (menuChanged) render();
  }

  async function syncTypingState(isTyping, force) {
    if (!state.activeChatter || activeChatterIsReadOnly() || !apiClient.token()) return;
    const now = Date.now();
    if (isTyping && !force && now - state.lastTypingPingAt < 2200) return;
    state.lastTypingPingAt = isTyping ? now : 0;
    try {
      await apiClient.post(`/api/chatters/${state.activeChatter}/typing`, { is_typing: !!isTyping });
    } catch (_) {}
  }

  function handleComposerKeydown(event) {
    if (event.key === "Escape" && state.mention.open) {
      state.mention = { open: false, query: "" };
      render();
    }
  }

  function insertMention(value) {
    const mention = `@${value}`;
    const before = String(state.composerBody || "").replace(/(^|\s)@[A-Za-z0-9_.-]*$/, (match, prefix) => `${prefix}${mention}`);
    state.composerBody = `${before} `;
    state.mention = { open: false, query: "" };
    render();
    window.setTimeout(() => {
      const input = document.querySelector(".composer input[name='body']");
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    }, 0);
  }

  function toggleChatterInfo(chatter) {
    if (!chatter) return;
    state.chatterInfoOpen = !state.chatterInfoOpen;
    render();
  }

  function updateAttachmentLabel(event) {
    clearPendingVoiceNote(false, true);
    state.pendingAttachment = event.target.files && event.target.files[0] ? event.target.files[0] : null;
    const label = event.target.closest(".file-chip");
    const text = label ? label.querySelector(".file-chip-text") : null;
    if (text) text.textContent = state.pendingAttachment?.name || "Attach";
  }

  function monitoringView() {
    if (!canManage()) return page([restricted("Monitoring is available to admins only.")]);
    const logs = filteredLogs();
    return page([
      h("section", { class: "metric-grid monitoring-metrics" }, [
        metric("Users", state.stats?.users || 0, "Users", "Current total"),
        metric("Projects", state.stats?.projects || 0, "FolderKanban", "Current total"),
        metric("Chatters", state.chatters.length, "MessagesSquare", "Current total"),
      ]),
      h("section", { class: "toolbar card activity-toolbar" }, [
        searchBox("Search activity logs", "logSearch"),
        filterSelect("logType", ["all", "project", "chatter", "message", "user", "login", "attachment"], "Type"),
      ]),
      h("article", { class: "card monitoring-activity-card" }, [cardHeader("Activity Log", "Audit events and workspace activity"), monitoringActivityList(logs)]),
    ]);
  }

  function filteredLogs() {
    const q = String(state.filters.logSearch || "").trim().toLowerCase();
    const type = state.filters.logType;
    return state.activityLogs.filter((log) => {
      const searchText = [
        log.id,
        log.activity_type,
        cleanLogType(log.activity_type),
        log.description,
        log.status,
        formatDate(log.created_at),
      ].join(" ").toLowerCase();
      const matchesSearch = !q || searchText.indexOf(q) >= 0;
      const matchesType = type === "all" || logTypeClass(log.activity_type) === type;
      return matchesSearch && matchesType;
    });
  }

  function activityList(items) {
    return items.length ? h("div", { class: "activity-list timeline" }, items.map((log) => h("div", { class: "activity-item" }, [
      h("span", { class: "timeline-icon" }, [icon("Activity", 14)]),
      h("span", { class: "activity-copy" }, [h("strong", {}, cap(log.activity_type || "Activity")), h("small", {}, log.description)]),
      h("time", {}, formatDate(log.created_at)),
    ]))) : h("div", { class: "dashboard-empty compact" }, [
      h("span", {}, [icon("Activity")]),
      h("strong", {}, "No recent activity"),
      h("p", {}, "Project, chatter, login, and user events will appear here."),
    ]);
  }

  function monitoringActivityList(items) {
    return items.length ? h("div", { class: "monitoring-feed" }, items.map((log) => h("article", { class: "monitoring-feed-item" }, [
      h("span", { class: `feed-type-dot ${logTypeClass(log.activity_type)}` }, [icon(logTypeIcon(log.activity_type), 15)]),
      h("div", { class: "feed-copy" }, [
        h("div", { class: "feed-line" }, [
          h("strong", {}, cleanLogType(log.activity_type)),
          h("span", { class: "feed-status" }, [h("i"), cap(log.status || "success")]),
        ]),
        h("p", {}, log.description || "Workspace activity recorded."),
      ]),
      h("time", {}, formatDate(log.created_at)),
    ]))) : h("div", { class: "dashboard-empty compact" }, [
      h("span", {}, [icon("Activity")]),
      h("strong", {}, "No activity yet"),
      h("p", {}, "Audit events and workspace activity will appear here."),
    ]);
  }

  function cleanLogType(type) {
    return cap(String(type || "activity").replace(/_(created|updated|deleted|sent)$/i, ""));
  }

  function logTypeClass(type) {
    const value = String(type || "").toLowerCase();
    if (value.indexOf("attachment") >= 0 || value.indexOf("file") >= 0) return "attachment";
    if (value.indexOf("project") >= 0) return "project";
    if (value.indexOf("chatter") >= 0) return "chatter";
    if (value.indexOf("message") >= 0) return "message";
    if (value.indexOf("user") >= 0) return "user";
    if (value.indexOf("login") >= 0) return "login";
    return "activity";
  }

  function logTypeIcon(type) {
    const value = logTypeClass(type);
    if (value === "project") return "FolderKanban";
    if (value === "chatter" || value === "message") return "MessagesSquare";
    if (value === "user") return "Users";
    if (value === "login") return "LogOut";
    if (value === "attachment") return "Paperclip";
    return "Activity";
  }

  function usersView() {
    const users = filteredUsers();
    return page([
      h("section", { class: "users-toolbar card" }, [
        searchBox("Search users...", "userSearch"),
        isAdmin() ? h("button", { class: "btn btn-primary users-create-btn", onclick: () => openModal("user") }, [icon("UserPlus"), "Create User"]) : null,
      ]),
      h("article", { class: "card users-card" }, [
        cardHeader("Users & Roles", "Access control and account status"),
        users.length ? usersTable(users) : usersEmptyState(),
      ]),
    ]);
  }

  function filteredUsers() {
    const q = state.filters.userSearch.toLowerCase();
    return state.users.filter((u) => {
      if (Number(u.id) === Number(state.user?.id)) return false;
      return !q || [u.name, u.email, u.login, roles(u).join(" "), displayRoles(u).join(" ")].join(" ").toLowerCase().indexOf(q) >= 0;
    });
  }

  function userRow(user) {
    return [
      h("div", { class: "user-person" }, [
        h("span", { class: `avatar user-avatar presence-avatar presence-${user.messenger_status || "offline"}` }, initials(user.name)),
        h("span", { class: "user-name-stack" }, [h("strong", {}, user.name), h("small", {}, user.login || user.email)]),
      ]),
      h("span", { class: "user-email" }, [icon("Mail", 15), user.email]),
      h("div", { class: "badge-row" }, roles(user).map((role) => badge(role, "role"))),
      userStatusBadge(user),
      formatDate(user.created_at),
      isAdmin() ? h("div", { class: "row-actions" }, [
        h("button", { class: "btn btn-outline action-role", onclick: () => openModal("role", user) }, [icon("Edit"), "Edit"]),
        user.id !== state.user.id && user.active ? h("button", { class: "btn btn-danger action-danger", onclick: () => confirmAction("Deactivate user?", "The user will no longer be active.", () => disableUser(user.id)) }, [icon("Trash"), "Deactivate"]) : null,
        user.id !== state.user.id && !user.active ? h("button", { class: "btn btn-primary", onclick: () => confirmAction("Activate user?", "This restores the user's workspace access.", () => activateUser(user.id)) }, [icon("Check"), "Activate"]) : null,
        user.id !== state.user.id ? h("button", { class: "btn btn-danger action-danger", onclick: () => confirmAction("Delete user?", "This permanently removes the user account.", () => deleteUser(user.id)) }, [icon("Trash"), "Delete"]) : null,
      ]) : "",
    ];
  }

  function userStatusBadge(user) {
    if (!user.active) return badge("inactive", "status");
    const status = String(user.messenger_status || "offline").toLowerCase();
    return h("span", { class: `presence-badge presence-${status}` }, [h("i"), cap(status)]);
  }

  function usersTable(users) {
    return h("div", { class: "table-wrap users-table-wrap" }, [h("table", { class: "users-table" }, [
      h("thead", {}, h("tr", {}, ["Name", "Email", "Role", "Status", "Created", "Actions"].map((head) => h("th", {}, head)))),
      h("tbody", {}, users.map((user) => h("tr", {}, userRow(user).map((cell, i) => h("td", { "data-label": ["Name", "Email", "Role", "Status", "Created", "Actions"][i] }, cell))))),
    ])]);
  }

  function usersEmptyState() {
    return h("div", { class: "users-empty-state" }, [
      h("span", { class: "empty-illustration" }, [icon("Users", 34)]),
      h("h2", {}, "No users found"),
      h("p", {}, "Try adjusting your search or create a new user."),
      isAdmin() ? h("button", { class: "btn btn-primary users-create-btn", onclick: () => openModal("user") }, [icon("UserPlus"), "Create User"]) : null,
    ]);
  }

  function filesView() {
    return page([
      h("article", { class: "card" }, [cardHeader("Upload Attachment", "Store files locally and link them to projects or chatters"), fileForm()]),
      h("article", { class: "card" }, [cardHeader("Uploaded Files", "Download or remove stored attachments"), responsiveTable(["File", "Type", "Size", "Project", "Chatter", "Actions"], state.files.map(fileRow))]),
    ]);
  }

  function fileRow(file) {
    return [
      h("div", { class: "person-cell" }, [icon("Paperclip"), h("span", {}, file.filename)]),
      file.content_type,
      prettyBytes(file.size_bytes),
      projectName(file.project_id),
      chatterName(file.chatter_id),
      h("div", { class: "row-actions" }, [
        h("button", { class: "btn btn-soft", onclick: () => downloadAttachment(file) }, "Download"),
        h("button", { class: "btn btn-danger", onclick: () => confirmAction("Delete file?", "This removes the local file and metadata.", () => deleteFile(file.id)) }, [icon("Trash"), "Delete"]),
      ]),
    ];
  }

  function fileForm() {
    return h("form", { class: "form-grid", onsubmit: uploadFile }, [
      field("File", h("input", { type: "file", name: "file", required: true })),
      field("Project", selectProjects("project_id", "No project")),
      field("Chatter", selectChatters("chatter_id", "No chatter")),
      h("button", { class: "btn btn-primary align-end" }, [icon("Paperclip"), "Upload"]),
    ]);
  }

  function emailView() {
    if (!canManage()) return page([restricted("Email logs are available to admins only.")]);
    return page([
      h("article", { class: "card" }, [cardHeader("Inbound Email Test", "Record inbound email payloads"), emailForm()]),
      h("article", { class: "card" }, [cardHeader("Email Logs", "Captured inbound messages"), responsiveTable(["From", "To", "Subject", "Status", "Date"], state.emailLogs.map((log) => [log.email_from || "", log.email_to || "", log.subject || "", badge(log.status), formatDate(log.created_at)]))]),
    ]);
  }

  function emailForm() {
    return h("form", { class: "form-grid", onsubmit: createEmail }, [
      field("From", h("input", { name: "email_from", placeholder: "sender@company.com" })),
      field("To", h("input", { name: "email_to", placeholder: "workspace@company.com" })),
      field("Subject", h("input", { name: "subject", placeholder: "Subject" })),
      field("Body", h("input", { name: "body", placeholder: "Message preview" })),
      h("button", { class: "btn btn-primary align-end" }, "Record"),
    ]);
  }

  function operationsView() {
    return page([
      h("section", { class: "ops-grid" }, [
        opsPanel("Tasks", state.operations.tasks, ["name", "stage", "priority"]),
        opsPanel("Documents", state.operations.documents, ["name", "access_level", "version"]),
        opsPanel("Incidents", state.operations.incidents, ["name", "state", "priority"]),
        opsPanel("Knowledge", state.operations.knowledge, ["title", "state", "version"]),
      ]),
    ]);
  }

  function opsPanel(title, rows, keys) {
    return h("article", { class: "card" }, [cardHeader(title, "Migrated operational records"), rows.length ? responsiveTable(keys.map(cap), rows.map((row) => keys.map((key) => row[key] || ""))) : emptyState("No records yet.")]);
  }

  function modalView() {
    const modal = state.modal;
    return h("div", { class: "modal-backdrop", onclick: closeModal }, [
      h("section", { class: modalClass(modal), onclick: (event) => event.stopPropagation() }, [
        h("div", { class: "modal-head" }, [h("h2", {}, modalTitle(modal)), h("button", { class: "icon-btn", onclick: closeModal }, [icon("X")])]),
        modal.type === "project" ? projectForm(modal.data) : null,
        modal.type === "chatter" ? chatterForm(modal.data) : null,
        modal.type === "user" ? userForm() : null,
        modal.type === "role" ? roleForm(modal.data) : null,
        modal.type === "profile" ? profileBody(modal.data || state.user) : null,
        modal.type === "chatterDetails" ? chatterDetailsBody(modal.chatter) : null,
        modal.type === "messageInfo" ? messageInfoBody(modal.message) : null,
        modal.type === "imagePreview" ? imagePreviewBody(modal.file) : null,
        modal.type === "confirm" ? confirmBody(modal) : null,
      ]),
    ]);
  }

  function modalClass(modal) {
    if (modal.type === "chatterDetails") return "modal chatter-detail-modal";
    if (modal.type === "messageInfo") return "modal message-info-modal";
    if (modal.type === "imagePreview") return "modal image-preview-modal";
    return "modal";
  }

  function modalTitle(modal) {
    if (modal.type === "project") return modal.data ? "Edit Project" : "Create Project";
    if (modal.type === "chatter") return modal.data ? "Edit Chatter" : "Create Chatter";
    if (modal.type === "user") return "Create User";
    if (modal.type === "role") return "Edit User";
    if (modal.type === "profile") return "Account Info";
    if (modal.type === "chatterDetails") return "Chatter Info";
    if (modal.type === "messageInfo") return "Message Info";
    if (modal.type === "imagePreview") return modal.file?.filename || "Image preview";
    return modal.title || "Confirm";
  }

  function openModal(type, data) {
    state.modal = { type, data: data || null };
    render();
  }

  function closeModal() {
    state.modal = null;
    render();
  }

  function confirmAction(title, message, action) {
    state.modal = { type: "confirm", title, message, action };
    render();
  }

  function confirmBody(modal) {
    return h("div", { class: "confirm-body" }, [
      h("p", {}, modal.message),
      h("div", { class: "modal-actions" }, [
        h("button", { type: "button", class: "btn btn-soft", onclick: closeModal }, "Cancel"),
        h("button", { type: "button", class: "btn btn-danger", onclick: async () => { const fn = modal.action; closeModal(); await fn(); } }, "Confirm"),
      ]),
    ]);
  }

  function imagePreviewBody(file) {
    const src = state.attachmentPreviews[file?.id];
    return h("div", { class: "image-lightbox-body" }, [
      h("div", { class: "image-lightbox-frame" }, [
        src
          ? h("img", { src, alt: file?.filename || "Image attachment" })
          : h("div", { class: "image-lightbox-loading" }, [icon("Image", 28), h("span", {}, "Loading image...")]),
      ]),
      h("div", { class: "image-lightbox-footer" }, [
        h("span", {}, [
          h("strong", {}, file?.filename || "Image attachment"),
          h("small", {}, `${prettyBytes(file?.size_bytes || 0)} Â· ${formatDate(file?.created_at)}`),
        ]),
        h("button", { type: "button", class: "btn btn-primary image-download-btn", title: "Download image", onclick: () => downloadAttachment(file) }, [
          icon("Download", 16),
          h("span", {}, "Download"),
        ]),
      ]),
    ]);
  }

  function profileBody(user) {
    const currentUser = Number(user?.id) === Number(state.user?.id);
    return h("div", { class: "profile-modal-body" }, [
      h("div", { class: "profile-modal-hero" }, [
        h("span", { class: `avatar profile-modal-avatar presence-avatar presence-${user?.messenger_status || "offline"}` }, initials(user?.name || "User")),
        h("div", {}, [
          h("h3", {}, user?.name || "User"),
          h("p", {}, user?.email || user?.login || ""),
          h("div", { class: "badge-row" }, roles(user).map((role) => badge(role, "role"))),
        ]),
      ]),
      h("div", { class: "profile-detail-grid" }, [
        profileDetail("Login", user?.login || "Not set", "UserRound"),
        profileDetail("Email", user?.email || "Not set", "Mail"),
        profileDetail("Account", user?.active ? "Active" : "Inactive", "Activity"),
        profileDetail("Created", formatDate(user?.created_at) || "Not available", "Calendar"),
      ]),
      currentUser ? accountSettingsForm(user) : null,
      h("div", { class: "modal-actions profile-modal-actions" }, [
        isAdmin() ? h("button", { type: "button", class: "btn btn-outline", onclick: () => { const current = state.users.find((item) => item.id === user?.id) || user; openModal("role", current); } }, [icon("Edit"), "Edit account"]) : null,
        h("button", { type: "button", class: "btn btn-primary", onclick: closeModal }, "Done"),
      ]),
    ]);
  }

  function accountSettingsForm(user) {
    return h("form", { class: "account-settings-form", onsubmit: saveOwnAccount }, [
      h("div", { class: "account-settings-head" }, [
        h("span", {}, [icon("ShieldCheck", 16)]),
        h("div", {}, [h("strong", {}, "Account security"), h("small", {}, "Update your password.")]),
      ]),
      h("div", { class: "form-grid account-settings-grid" }, [
        field("New password", inputWrap("Lock", h("input", { name: "password", type: "password", placeholder: "Leave blank to keep current", minlength: "8", autocomplete: "new-password" }))),
      ]),
      h("button", { type: "submit", class: "btn btn-primary account-save-btn" }, [icon("Check"), "Save changes"]),
      pushSettingsPanel(),
    ]);
  }

  function pushSettingsPanel() {
    const prefs = state.notificationPreferences || {};
    const supported = pushSupported();
    const configured = !!state.pushConfig?.enabled;
    const enabled = !!prefs.browser_push_enabled;
    return h("div", { class: "push-settings-panel" }, [
      h("div", { class: "account-settings-head" }, [
        h("span", {}, [icon("Bell", 16)]),
        h("div", {}, [h("strong", {}, "Push notifications"), h("small", {}, pushStatusText(supported, configured, enabled))]),
      ]),
      h("div", { class: "push-toggle-row" }, [
        h("button", {
          type: "button",
          class: enabled ? "btn btn-outline" : "btn btn-primary",
          disabled: state.pushBusy || !supported || !configured,
          onclick: enabled ? disablePushNotifications : enablePushNotifications,
        }, [icon(enabled ? "BellOff" : "Bell"), state.pushBusy ? "Saving..." : (enabled ? "Disable push" : "Enable push")]),
      ]),
      h("label", { class: "check-row" }, [
        h("input", { type: "checkbox", checked: !!prefs.push_chatter_messages, onchange: (event) => saveNotificationPreference("push_chatter_messages", event.target.checked) }),
        h("span", {}, [h("strong", {}, "Chatter messages"), h("small", {}, "Notify me when someone sends a message in my conversations.")]),
      ]),
      h("label", { class: "check-row" }, [
        h("input", { type: "checkbox", checked: !!prefs.push_workspace_updates, onchange: (event) => saveNotificationPreference("push_workspace_updates", event.target.checked) }),
        h("span", {}, [h("strong", {}, "Workspace updates"), h("small", {}, "Notify me about important project and account updates.")]),
      ]),
    ]);
  }

  function pushStatusText(supported, configured, enabled) {
    if (!supported) return "This browser does not support web push.";
    if (!configured) return "Add VAPID keys on the backend to enable browser or mobile push.";
    return enabled ? "Enabled for this account." : "Off until you enable it for this browser.";
  }

  function profileDetail(label, value, iconName) {
    return h("div", { class: "profile-detail" }, [
      h("span", {}, [icon(iconName, 15)]),
      h("div", {}, [h("small", {}, label), h("strong", {}, value)]),
    ]);
  }

  function chatterDetailsBody(chatter) {
    const members = chatter?.members || [];
    const allFiles = sharedChatterFiles(chatter);
    const images = allFiles.filter((file) => String(file.content_type || "").startsWith("image/"));
    const documents = allFiles.filter((file) => !String(file.content_type || "").startsWith("image/"));
    return h("div", { class: "chatter-detail-body" }, [
      h("div", { class: "chatter-detail-hero" }, [
        h("span", { class: "chatter-detail-avatar" }, initials(chatter?.name || "Chatter")),
        h("div", {}, [
          h("h3", {}, chatter?.name || "Chatter"),
          h("p", {}, chatter?.description || "No description added."),
          h("small", {}, `Created ${formatDate(chatter?.created_at)}`),
        ]),
      ]),
      h("div", { class: "detail-section" }, [
        h("div", { class: "detail-section-head" }, [h("h4", {}, "Members"), h("span", {}, `${members.length}`)]),
        members.length ? h("div", { class: "detail-member-list" }, members.map((member) => h("div", { class: "detail-member" }, [
          h("span", { class: "member-mini-avatar" }, initials(member.name || member.email)),
          h("span", {}, [h("strong", {}, member.name || member.email), h("small", {}, displayRoles(member).join(", ") || "Member")]),
        ]))) : detailEmpty("No members assigned."),
      ]),
      h("div", { class: "detail-section" }, [
        h("div", { class: "detail-section-head" }, [h("h4", {}, "Shared screenshots/images"), h("span", {}, `${images.length}`)]),
        images.length ? h("div", { class: "detail-file-grid" }, images.map(detailFile)) : detailEmpty("No shared screenshots or images."),
      ]),
      h("div", { class: "detail-section" }, [
        h("div", { class: "detail-section-head" }, [h("h4", {}, "Shared documents/files"), h("span", {}, `${documents.length}`)]),
        documents.length ? h("div", { class: "detail-file-list" }, documents.map(detailFile)) : detailEmpty("No shared documents or files."),
      ]),
    ]);
  }

  function sharedChatterFiles(chatter) {
    const byId = new Map();
    (state.files || []).filter((file) => Number(file.chatter_id) === Number(chatter?.id)).forEach((file) => byId.set(file.id, file));
    (state.messages || []).forEach((message) => (message.attachments || []).forEach((file) => byId.set(file.id, file)));
    return Array.from(byId.values()).sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }

  function detailFile(file) {
    const image = isImageFile(file);
    return h("button", { type: "button", class: "detail-file", onclick: () => image ? openImagePreview(file) : downloadAttachment(file) }, [
      image ? h("span", { class: "detail-image-icon" }, [icon("Image", 16)]) : fileTypeBadge(file),
      h("span", {}, [h("strong", {}, file.filename || "Attachment"), h("small", {}, `${prettyBytes(file.size_bytes || 0)} Â· ${formatDate(file.created_at)}`)]),
    ]);
  }

  function messageInfoBody(message) {
    const viewers = messageSeenViewers(message);
    const sentAt = message?.created_at ? `${formatDate(message.created_at)} at ${formatMessageTime(message.created_at)}` : "Unknown";
    return h("div", { class: "message-info-body" }, [
      h("div", { class: "message-info-summary" }, [
        h("span", { class: "message-info-icon" }, [icon("Check", 16)]),
        h("span", {}, [h("strong", {}, "Sent"), h("small", {}, sentAt)]),
      ]),
      h("div", { class: "message-info-section" }, [
        h("div", { class: "message-info-title" }, [
          h("span", {}, "Read by"),
          h("small", {}, String(viewers.length)),
        ]),
        viewers.length ? h("div", { class: "message-info-list" }, viewers.map((user) => h("div", { class: "message-info-person" }, [
          h("span", { class: "member-mini-avatar" }, initials(user.name || user.email || user.login || "User")),
          h("span", {}, [
            h("strong", {}, user.name || user.login || user.email || `User ${user.id}`),
            h("small", {}, user.email || displayRoles(user).join(", ") || "Seen"),
          ]),
        ]))) : h("div", { class: "message-info-empty" }, [
          icon("Eye", 16),
          h("span", {}, "No one has seen this message yet."),
        ]),
      ]),
    ]);
  }

  function detailEmpty(text) {
    return h("div", { class: "detail-empty" }, [icon("Paperclip", 16), h("span", {}, text)]);
  }

  function projectForm(project) {
    return h("form", { class: "form-grid project-modal-form", onsubmit: (event) => saveProject(event, project) }, [
      h("label", { class: "field form-span" }, [h("span", {}, "Project name"), inputWrap("FolderKanban", h("input", { name: "name", value: project?.name || "", placeholder: "Enter project name", required: true }))]),
      field("Status", inputWrap("Activity", select("status", ["active", "completed"], project?.status || "active"), h("span", { class: "status-dot active" }))),
      field("Priority", inputWrap("ChevronsUpDown", select("priority", ["low", "normal", "high", "urgent"], project?.priority || "normal"))),
      field("Deadline", inputWrap("Calendar", h("input", { type: "date", name: "deadline", value: project?.deadline || "", placeholder: "mm/dd/yyyy" }))),
      field("Customer", inputWrap("Users", selectCustomersMulti("customer_ids", "Add customer", project?.customer_id ? [project.customer_id] : []))),
      field("Add member", inputWrap("UserPlus", selectUsersMulti("member_ids", "Add member", project?.members?.filter((user) => !isCustomerUser(user))?.map((user) => user.id) || [], { excludeCustomers: true }))),
      field("Read-only members", inputWrap("Eye", selectUsersMulti("read_only_member_ids", "Select read-only users", project?.read_only_member_ids || [], { excludeCustomers: true }))),
      h("div", { class: "modal-actions form-span project-modal-footer" }, [
        h("button", { type: "button", class: "btn btn-soft", onclick: closeModal }, "Cancel"),
        h("button", { class: "btn btn-primary project-submit-btn" }, [project ? "Save Project" : "Create Project", icon("ChevronRight", 16)]),
      ]),
    ]);
  }

  function chatterForm(chatter) {
    const chatterProject = chatter?.project_id ? state.projects.find((project) => Number(project.id) === Number(chatter.project_id)) : null;
    return h("form", { class: "form-grid chatter-modal-form", onsubmit: (event) => saveChatter(event, chatter) }, [
      field("Name", inputWrap("MessagesSquare", h("input", { name: "name", value: chatter?.name || "", placeholder: "Enter chatter name", required: true }))),
      chatter ? field("Project", inputWrap("FolderKanban", h("div", { class: "readonly-field" }, [
        h("span", { class: "readonly-field-label" }, chatterProject?.name || "No project"),
        h("small", {}, "Linked project only"),
      ]))) : field("Project", inputWrap("FolderKanban", selectProjects("project_id", "No project"))),
      field("Member", inputWrap("UserPlus", selectUsersMulti("member_ids", "Optional members", chatter?.members?.map((user) => user.id) || []))),
      field("Read-only members", inputWrap("Eye", selectUsersMulti("read_only_member_ids", "Select read-only users", chatter?.read_only_member_ids || []))),
      h("div", { class: "modal-actions form-span user-modal-footer" }, [
        h("button", { type: "button", class: "btn btn-soft", onclick: closeModal }, "Cancel"),
        h("button", { class: "btn btn-primary user-submit-btn" }, [icon(chatter ? "Check" : "MessageCircle", 16), chatter ? "Save Chatter" : "Create Chatter"]),
      ]),
    ]);
  }

  function userForm() {
    return h("form", { class: "form-grid user-modal-form", onsubmit: createUser, autocomplete: "off" }, [
      field("Name", inputWrap("UserRound", h("input", { name: "name", placeholder: "Enter full name", required: true, autocomplete: "new-user-name" }))),
      field("Email", inputWrap("Mail", h("input", { name: "email", type: "email", placeholder: "name@company.com", required: true, autocomplete: "new-user-email" }))),
      field("Password", inputWrap("Lock", h("input", { name: "password", type: "password", placeholder: "Minimum 8 characters", required: true, minlength: "8", autocomplete: "new-password" }))),
      field("Role", inputWrap("Users", roleSelect("role", "customer"))),
      h("label", { class: "check-row form-span" }, [
        h("input", { type: "checkbox", name: "read_only", value: "true" }),
        h("span", {}, [h("strong", {}, "Read-only access"), h("small", {}, "User can view assigned workspace data but cannot create, edit, delete, message, or upload.")]),
      ]),
      h("div", { class: "modal-actions form-span user-modal-footer" }, [
        h("button", { type: "button", class: "btn btn-soft", onclick: closeModal }, "Cancel"),
        h("button", { class: "btn btn-primary user-submit-btn" }, [icon("UserPlus", 16), "Create User"]),
      ]),
    ]);
  }

  function roleForm(user) {
    return h("form", { class: "form-grid role-modal-form", onsubmit: (event) => saveRole(event, user) }, [
      h("div", { class: "form-span role-user-card" }, [
        h("span", { class: "avatar user-avatar" }, initials(user.name)),
        h("span", {}, [h("strong", {}, user.name), h("small", {}, user.email || user.login)]),
      ]),
      field("Name", inputWrap("UserRound", h("input", { name: "name", value: user.name || "", placeholder: "Enter full name", required: true }))),
      field("Email", inputWrap("Mail", h("input", { name: "email", type: "email", value: user.email || "", placeholder: "name@company.com", required: true }))),
      field("Password", inputWrap("Lock", h("input", { name: "password", type: "password", placeholder: "Leave blank to keep current password", minlength: "8", autocomplete: "new-password" }))),
      field("Role", inputWrap("Users", roleSelect("role", normalizeRole(roles(user)[0] || "customer")))),
      h("label", { class: "check-row form-span" }, [
        h("input", { type: "checkbox", name: "read_only", value: "true", checked: !!user.read_only }),
        h("span", {}, [h("strong", {}, "Read-only access"), h("small", {}, "User can view assigned workspace data but cannot create, edit, delete, message, or upload.")]),
      ]),
      h("div", { class: "modal-actions form-span user-modal-footer" }, [
        h("button", { type: "button", class: "btn btn-soft", onclick: closeModal }, "Cancel"),
        h("button", { class: "btn btn-primary user-submit-btn" }, [icon("Check", 16), "Save Changes"]),
      ]),
    ]);
  }

  async function saveProject(event, project) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());
    const memberIds = formData.getAll("member_ids").filter(Boolean).map(Number);
    const readOnlyMemberIds = formData.getAll("read_only_member_ids").filter(Boolean).map(Number);
    const customerIds = formData.getAll("customer_ids").filter(Boolean).map(Number);
    const allMemberIds = Array.from(new Set([state.user.id].concat(memberIds, customerIds, readOnlyMemberIds)));
    await run(async () => {
      const payload = {
        name: data.name,
        code: project?.code || null,
        status: data.status,
        priority: data.priority,
        deadline: data.deadline || null,
        customer_id: customerIds[0] || null,
        manager_id: state.user.id,
        member_ids: allMemberIds,
        read_only_member_ids: readOnlyMemberIds,
      };
      if (project) await apiClient.put(`/api/projects/${project.id}`, payload);
      else {
        const savedProject = await apiClient.post("/api/projects", payload);
        await ensureProjectChatter(savedProject, payload);
      }
      closeModal();
      await Promise.all([loadProjects(), loadChatters()]);
    }, project ? "Project updated." : "Project created.");
  }

  async function ensureProjectChatter(project, payload) {
    if (!project?.id) return;
    await loadChatters();
    if (state.chatters.some((chatter) => Number(chatter.project_id) === Number(project.id))) return;
    const memberIds = Array.from(new Set([
      ...(payload.member_ids || []),
      payload.manager_id,
      payload.customer_id,
    ].filter(Boolean).map(Number)));
    await apiClient.post("/api/chatters", {
      name: project.name,
      project_id: project.id,
      member_ids: memberIds,
      read_only_member_ids: payload.read_only_member_ids || [],
    });
  }

  async function deleteProject(id) {
    await run(async () => {
      await apiClient.del(`/api/projects/${id}`);
      if (state.activeChatter && state.chatters.some((chatter) => sameId(chatter.project_id, id) && sameId(chatter.id, state.activeChatter))) {
        clearActiveChatter();
      }
      await Promise.all([loadProjects(), loadChatters()]);
    }, "Project deleted.");
  }

  async function saveChatter(event, chatter) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());
    const selectedMemberIds = formData.getAll("member_ids").filter(Boolean).map(Number);
    const readOnlyMemberIds = formData.getAll("read_only_member_ids").filter(Boolean).map(Number);
    const memberIds = chatter ? selectedMemberIds.concat(readOnlyMemberIds) : [state.user.id].concat(selectedMemberIds, readOnlyMemberIds);
    await run(async () => {
      const payload = {
        name: data.name,
        project_id: chatter ? (chatter.project_id ? Number(chatter.project_id) : null) : (data.project_id ? Number(data.project_id) : null),
        member_ids: Array.from(new Set(memberIds)),
        read_only_member_ids: Array.from(new Set(readOnlyMemberIds)),
      };
      if (chatter) await apiClient.put(`/api/chatters/${chatter.id}`, payload);
      else await apiClient.post("/api/chatters", payload);
      closeModal();
      await loadChatters();
    }, chatter ? "Chatter updated." : "Chatter created.");
  }

  async function selectChatter(id) {
    if (sameId(state.activeChatter, id) && state.messages.length) return;
    try {
      setActiveChatter(id);
      state.mention = { open: false, query: "" };
      state.replyTo = null;
      state.editingMessage = null;
      state.editingBody = "";
      state.openMessageMenu = null;
      state.pendingVoiceDuration = null;
      state.messages = await apiClient.get(`/api/chatters/${id}/messages`);
      markChatterReadLocally(id);
      state.lastMessageSignature = messageSignature(state.messages);
      state.scrollMessagesBottom = true;
      render();
    } catch (err) {
      const message = err.message || String(err);
      state.error = message;
      toast(message, "error");
      render();
    }
  }

  async function openChatter(id) {
    if (state.tab === "chatters" && sameId(state.activeChatter, id) && state.messages.length) return;
    if (state.activeChatter && state.composerBody.trim()) await syncTypingState(false, true);
    cancelVoiceRecording(true);
    setActiveChatter(id);
    state.tab = "chatters";
    state.pendingAttachment = null;
    state.pendingVoiceDuration = null;
    state.replyTo = null;
    state.editingMessage = null;
    state.editingBody = "";
    state.chatInfoExpanded = { members: false, images: false, documents: false };
    state.openMessageMenu = null;
    state.typingUsers = [];
    state.lastTypingPingAt = 0;
    localStorage.setItem("anochat_tab", "chatters");
    state.scrollMessagesBottom = true;
    await run(() => loadTab("chatters"));
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (state.sendingMessage) return;
    const chatterId = state.activeChatter;
    if (!chatterId) {
      toast("Select a conversation first.", "error");
      render();
      return;
    }
    if (activeChatterIsReadOnly()) {
      toast("This chatter is read-only for your account.", "error");
      render();
      return;
    }
    const data = new FormData(event.target);
    const file = state.pendingAttachment || data.get("file");
    const attachmentIds = [];
    state.sendingMessage = true;
    state.error = "";
    try {
      if (file && file.size) {
        const upload = new FormData();
        upload.append("file", file);
        upload.append("chatter_id", chatterId);
        if (state.pendingVoiceDuration) upload.append("duration_seconds", String(state.pendingVoiceDuration));
        const saved = await apiClient.post("/api/attachments/upload", upload);
        attachmentIds.push(saved.id);
      }
      const body = data.get("body") || (state.pendingVoiceDuration ? "Voice note" : (attachmentIds.length ? "Attachment" : ""));
      if (!body.trim() && !attachmentIds.length) throw new Error("Write a message or attach a file.");
      if (hasContactDetails(body)) toast("Contact details are not allowed in chatter and will be hidden.", "success");
      const replyToId = state.replyTo && Number(state.replyTo.chatter_id) === Number(chatterId) ? state.replyTo.id : null;
      const savedMessage = await apiClient.post(`/api/chatters/${chatterId}/messages`, { body, attachment_ids: attachmentIds, reply_to_id: replyToId });
      await syncTypingState(false, true);
      event.target.reset();
      state.composerBody = "";
      state.pendingAttachment = null;
      state.pendingVoiceDuration = null;
      if (state.pendingVoicePreviewUrl) URL.revokeObjectURL(state.pendingVoicePreviewUrl);
      state.pendingVoicePreviewUrl = null;
      state.replyTo = null;
      state.mention = { open: false, query: "" };
      if (sameId(state.activeChatter, chatterId)) {
        state.messages = state.messages.concat(savedMessage);
        const current = state.chatters.find((item) => sameId(item.id, chatterId));
        if (current) {
          current.last_message_preview = savedMessage.body;
          current.last_message_author_id = savedMessage.sender_id;
        }
        if (attachmentIds.length) state.messages = await apiClient.get(`/api/chatters/${chatterId}/messages`);
        state.lastMessageSignature = messageSignature(state.messages);
        setActiveChatter(chatterId);
      }
      state.scrollMessagesBottom = true;
    } catch (err) {
      const message = err.message || String(err);
      state.error = message;
      toast(message, "error");
    } finally {
      state.sendingMessage = false;
      render();
    }
  }

  async function deleteMessage(id) {
    const chatterId = state.activeChatter;
    try {
      const deleted = await apiClient.del(`/api/messages/${id}`);
      state.messages = state.messages.map((message) => sameId(message.id, id) ? deleted : message);
      if (state.editingMessage && Number(state.editingMessage.id) === Number(id)) {
        state.editingMessage = null;
        state.editingBody = "";
      }
      state.lastMessageSignature = messageSignature(state.messages);
      if (chatterId) {
        const current = state.chatters.find((item) => sameId(item.id, chatterId));
        const visibleMessages = state.messages;
        const last = visibleMessages[visibleMessages.length - 1];
        if (current) {
          current.last_message_preview = last ? last.body : "";
          current.last_message_author_id = last ? last.sender_id : null;
        }
      }
      toast("Message deleted.", "success");
    } catch (err) {
      const message = err.message || String(err);
      state.error = message;
      toast(message, "error");
    } finally {
      render();
    }
  }

  async function saveEditedMessage(event, message) {
    event.preventDefault();
    if (!canEditMessage(message)) {
      toast("Message edit window has expired.", "error");
      state.editingMessage = null;
      state.editingBody = "";
      render();
      return;
    }
    const body = String(state.editingBody || "").trim();
    if (!body) {
      toast("Edited message cannot be empty.", "error");
      render();
      return;
    }
    try {
      const updated = await apiClient.put(`/api/messages/${message.id}`, { body });
      state.messages = state.messages.map((item) => Number(item.id) === Number(message.id) ? updated : item);
      state.lastMessageSignature = messageSignature(state.messages);
      state.editingMessage = null;
      state.editingBody = "";
      const current = state.chatters.find((item) => Number(item.id) === Number(updated.chatter_id));
      if (current) current.last_message_preview = updated.body;
      toast("Message updated.", "success");
    } catch (err) {
      const text = err.message || String(err);
      state.error = text;
      toast(text, "error");
    } finally {
      render();
    }
  }

  async function downloadAttachment(file) {
    await run(async () => {
      const blob = await apiClient.get(`/api/attachments/${file.id}`);
      const url = URL.createObjectURL(blob);
      const link = h("a", { href: url, download: file.filename || "attachment" });
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }

  async function deleteChatter(id) {
    await run(async () => {
      await apiClient.del(`/api/chatters/${id}`);
      clearActiveChatter();
      await loadChatters();
    }, "Chatter deleted.");
  }

  async function createUser(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    const email = String(data.email || "").trim().toLowerCase();
    const role = String(data.role || "customer").trim() || "customer";
    if (!String(data.name || "").trim() || !email || !String(data.password || "").trim()) {
      toast("Name, email, and password are required.", "error");
      render();
      return;
    }
    if (!isValidEmail(email)) {
      toast("Enter a valid email address before saving the user.", "error");
      render();
      return;
    }
    if (looksLikeGmailTypo(email)) {
      toast("Please correct the email domain to @gmail.com.", "error");
      render();
      return;
    }
    if (email.endsWith("@gmail.com")) {
      toast("Gmail address accepted.", "success");
    }
    await run(async () => {
      await apiClient.post("/api/users", {
        name: String(data.name).trim(),
        email,
        login: email,
        password: data.password,
        read_only: data.read_only === "true",
        roles: [role],
      });
      closeModal();
      await loadUsers();
    }, "User created.");
  }

  async function saveOwnAccount(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    const password = String(data.password || "").trim();
    if (!password) {
      toast("Enter a new password to save.", "error");
      render();
      return;
    }
    if (password && password.length < 8) {
      toast("Password must be at least 8 characters.", "error");
      render();
      return;
    }
    await run(async () => {
      const payload = { password };
      const updated = await apiClient.put(`/api/users/${state.user.id}`, payload);
      state.user = updated;
      state.modal = { type: "profile", data: updated };
      if (state.users.length) state.users = state.users.map((user) => user.id === updated.id ? updated : user);
      state.chatters = state.chatters.map((chatter) => ({
        ...chatter,
        members: (chatter.members || []).map((member) => member.id === updated.id ? updated : member),
      }));
    }, "Password updated.");
  }

  function pushSupported() {
    return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  }

  function urlBase64ToUint8Array(value) {
    const padding = "=".repeat((4 - value.length % 4) % 4);
    const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
  }

  async function getPushRegistration() {
    return navigator.serviceWorker.register("static/push-sw.js");
  }

  async function enablePushNotifications() {
    if (!pushSupported()) {
      toast("This browser does not support push notifications.", "error");
      return;
    }
    if (!state.pushConfig?.enabled || !state.pushConfig.public_key) {
      toast("Push is not configured on the server yet.", "error");
      return;
    }
    state.pushBusy = true;
    render();
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") throw new Error("Notification permission was not granted.");
      const registration = await getPushRegistration();
      const existing = await registration.pushManager.getSubscription();
      const subscription = existing || await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(state.pushConfig.public_key),
      });
      await apiClient.post("/api/notifications/subscriptions", subscription.toJSON());
      const preferences = await apiClient.put("/api/notifications/preferences", { browser_push_enabled: true });
      state.notificationPreferences = preferences;
      toast("Push notifications enabled.", "success");
    } catch (err) {
      toast(err.message || "Could not enable push notifications.", "error");
    } finally {
      state.pushBusy = false;
      render();
    }
  }

  async function disablePushNotifications() {
    state.pushBusy = true;
    render();
    try {
      if (pushSupported()) {
        const registration = await getPushRegistration();
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) await subscription.unsubscribe();
      }
      const preferences = await apiClient.put("/api/notifications/preferences", { browser_push_enabled: false });
      state.notificationPreferences = preferences;
      toast("Push notifications disabled.", "success");
    } catch (err) {
      toast(err.message || "Could not disable push notifications.", "error");
    } finally {
      state.pushBusy = false;
      render();
    }
  }

  async function saveNotificationPreference(key, value) {
    try {
      const preferences = await apiClient.put("/api/notifications/preferences", { [key]: !!value });
      state.notificationPreferences = preferences;
      render();
    } catch (err) {
      toast(err.message || "Could not save notification preferences.", "error");
      render();
    }
  }

  async function savePresenceStatus(status) {
    const value = String(status || "offline").toLowerCase();
    if (!["online", "away", "busy", "offline"].includes(value)) {
      toast("Choose a valid presence status.", "error");
      render();
      return;
    }
    state.presenceOpen = false;
    render();
    try {
      const updated = await apiClient.put(`/api/users/${state.user.id}`, { messenger_status: value });
      state.user = updated;
      if (state.modal?.type === "profile") state.modal = { type: "profile", data: updated };
      if (state.users.length) state.users = state.users.map((user) => user.id === updated.id ? updated : user);
      state.chatters = state.chatters.map((chatter) => ({
        ...chatter,
        members: (chatter.members || []).map((member) => member.id === updated.id ? updated : member),
      }));
      broadcastPresenceChange(updated);
      await refreshPresenceData(true);
      toast("Status updated.", "success");
    } catch (err) {
      const message = err.message || String(err);
      toast(message, "error");
      render();
    }
  }

  function isValidEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(String(value || ""));
  }

  function looksLikeGmailTypo(value) {
    const domain = String(value || "").split("@")[1]?.toLowerCase() || "";
    if (!domain || domain === "gmail.com") return false;
    const compact = domain.replace(/[^a-z0-9]/g, "");
    return compact.indexOf("gmail") >= 0 || compact.indexOf("gmai") >= 0 || compact.indexOf("gmal") >= 0;
  }

  async function markNotificationsRead(event) {
    if (event) event.preventDefault();
    try {
      await apiClient.post("/api/notifications/read-all", {});
      state.notifications = [];
    } catch (err) {
      toast(err.message || "Could not update notifications.", "error");
    } finally {
      state.notificationsOpen = true;
      render();
    }
  }

  async function saveRole(event, user) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    const email = String(data.email || "").trim().toLowerCase();
    if (!String(data.name || "").trim() || !email) {
      toast("Name and email are required.", "error");
      render();
      return;
    }
    if (!isValidEmail(email)) {
      toast("Enter a valid email address before saving the user.", "error");
      render();
      return;
    }
    if (looksLikeGmailTypo(email)) {
      toast("Please correct the email domain to @gmail.com.", "error");
      render();
      return;
    }
    await run(async () => {
      const payload = {
        name: String(data.name).trim(),
        email,
        login: email,
        read_only: data.read_only === "true",
        roles: [data.role],
      };
      if (String(data.password || "").trim()) payload.password = data.password;
      await apiClient.put(`/api/users/${user.id}`, payload);
      closeModal();
      await loadUsers();
    }, "User updated.");
  }

  async function disableUser(id) {
    await run(async () => {
      await apiClient.put(`/api/users/${id}`, { active: false });
      await loadUsers();
    }, "User deactivated.");
  }

  async function activateUser(id) {
    await run(async () => {
      await apiClient.put(`/api/users/${id}`, { active: true });
      await loadUsers();
    }, "User activated.");
  }

  async function deleteUser(id) {
    await run(async () => {
      await apiClient.del(`/api/users/${id}`);
      await loadUsers();
    }, "User deleted.");
  }

  async function uploadFile(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    if (!form.get("project_id")) form.delete("project_id");
    if (!form.get("chatter_id")) form.delete("chatter_id");
    await run(async () => {
      await apiClient.post("/api/attachments/upload", form);
      event.target.reset();
      await loadFiles();
    }, "File uploaded.");
  }

  async function deleteFile(id) {
    await run(async () => {
      await apiClient.del(`/api/attachments/${id}`);
      await loadFiles();
    }, "File deleted.");
  }

  async function createEmail(event) {
    event.preventDefault();
    await run(async () => {
      await apiClient.post("/api/email/inbound", Object.fromEntries(new FormData(event.target).entries()));
      event.target.reset();
      await loadEmail();
    }, "Inbound email recorded.");
  }

  function page(children, className) { return h("main", { class: className ? `page ${className}` : "page" }, children); }
  function cardHeader(title, subtitle, actionLabel, action) {
    return h("div", { class: "card-head" }, [
      h("div", {}, [h("h2", {}, title), subtitle ? h("p", { class: "muted" }, subtitle) : null]),
      actionLabel ? h("button", { class: "btn btn-soft", onclick: action }, actionLabel) : null,
    ]);
  }
  function metaItem(label, value) { return h("div", {}, [h("span", {}, label), h("strong", {}, value)]); }
  function field(label, input) { return h("label", { class: "field" }, [h("span", {}, label), input]); }
  function searchBox(placeholder, key) {
    return h("label", { class: "search-box" }, [
      icon("Search"),
      h("input", {
        type: "search",
        placeholder,
        value: state.filters[key] || "",
        autocomplete: "off",
        "data-search-key": key,
        oninput: (e) => {
          state.filters[key] = e.target.value;
          render();
        },
      }),
    ]);
  }
  function filterSelect(key, values, label) {
    return h("label", { class: "filter-select" }, [
      icon("ChevronsUpDown", 16),
      h("span", {}, label || "Filter"),
      dropdown({
        value: state.filters[key],
        items: values.map((value) => ({ value, label: cap(value) })),
        onChange: (value) => { state.filters[key] = value; render(); },
      }),
    ]);
  }
  function select(name, values, selected) {
    return dropdown({ name, value: selected, items: values.map((value) => typeof value === "object" ? value : ({ value, label: cap(value) })) });
  }
  function roleSelect(name, selected) {
    return dropdown({ name, value: normalizeRole(selected), items: roleOptions() });
  }
  function selectUsers(name, label, selected) {
    return dropdown({
      name,
      value: selected || "",
      items: [{ value: "", label }].concat(state.users.map((u) => ({ value: u.id, label: `${u.name} (${displayRoles(u).join(", ") || "User"})` }))),
    });
  }
  function selectCustomers(name, label, selected) {
    const customers = state.users.filter((u) => roles(u).map(normalizeRole).indexOf("customer") >= 0);
    return dropdown({
      name,
      value: selected || "",
      items: [{ value: "", label }].concat(customers.map((u) => ({ value: u.id, label: `${u.name} (${u.login || u.email})` }))),
    });
  }
  function selectCustomersMulti(name, label, selected) {
    const customers = state.users.filter(isCustomerUser);
    return multiDropdown({
      name,
      placeholder: label,
      values: selected || [],
      items: customers.map((u) => ({ value: u.id, label: `${u.name} (${u.login || u.email})` })),
    });
  }
  function selectUsersMulti(name, label, selected, options) {
    const selectableUsers = options?.excludeCustomers ? state.users.filter((u) => !isCustomerUser(u)) : state.users;
    return multiDropdown({
      name,
      placeholder: label,
      values: selected || [],
      items: selectableUsers.map((u) => ({ value: u.id, label: `${u.name} (${displayRoles(u).join(", ") || "User"})` })),
    });
  }
  function isCustomerUser(user) {
    return roles(user).map(normalizeRole).indexOf("customer") >= 0;
  }
  function selectProjects(name, label, selected) {
    return dropdown({
      name,
      value: selected || "",
      items: [{ value: "", label }].concat(state.projects.map((p) => ({ value: p.id, label: p.name }))),
    });
  }
  function selectChatters(name, label, selected) {
    return dropdown({
      name,
      value: selected || "",
      items: [{ value: "", label }].concat(state.chatters.map((c) => ({ value: c.id, label: c.name }))),
    });
  }
  function dropdown(config) {
    const selectedValue = String(config.value ?? "");
    const items = (config.items || []).map((item) => ({ value: String(item.value ?? ""), label: item.label || cap(item.value) }));
    const selected = items.find((item) => item.value === selectedValue) || items[0] || { value: "", label: "Select" };
    const root = h("div", { class: "custom-select", tabindex: "-1" }, [
      config.name ? h("input", { type: "hidden", name: config.name, value: selected.value }) : null,
      h("button", { type: "button", class: "custom-select-trigger" }, [
        h("span", { class: "custom-select-label" }, selected.label),
        icon("ChevronsUpDown", 16),
      ]),
      h("div", { class: "custom-select-menu" }, items.map((item) => h("button", {
        type: "button",
        class: item.value === selected.value ? "custom-select-option active" : "custom-select-option",
        "data-value": item.value,
      }, item.label))),
    ]);
    const trigger = root.querySelector(".custom-select-trigger");
    const hidden = root.querySelector("input[type='hidden']");
    const label = root.querySelector(".custom-select-label");
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      document.querySelectorAll(".custom-select.open").forEach((selectEl) => { if (selectEl !== root) selectEl.classList.remove("open"); });
      root.classList.toggle("open");
    });
    root.querySelectorAll(".custom-select-option").forEach((option) => option.addEventListener("click", (event) => {
      event.preventDefault();
      const value = option.getAttribute("data-value") || "";
      const item = items.find((entry) => entry.value === value);
      if (hidden) hidden.value = value;
      if (label && item) label.textContent = item.label;
      root.querySelectorAll(".custom-select-option").forEach((entry) => entry.classList.toggle("active", entry === option));
      root.classList.remove("open");
      if (config.onChange) config.onChange(value);
    }));
    root.addEventListener("focusout", () => window.setTimeout(() => {
      if (!root.contains(document.activeElement)) root.classList.remove("open");
    }, 80));
    return root;
  }
  function multiDropdown(config) {
    const items = (config.items || []).map((item) => ({ value: String(item.value ?? ""), label: item.label || cap(item.value) }));
    const selectedValues = new Set((config.values || []).filter((value) => value !== null && value !== undefined && value !== "").map((value) => String(value)));
    const root = h("div", { class: "custom-select multi-select", tabindex: "-1" }, [
      h("span", { class: "multi-hidden-inputs" }),
      h("button", { type: "button", class: "custom-select-trigger" }, [
        h("span", { class: "custom-select-label" }, config.placeholder || "Select"),
        icon("ChevronsUpDown", 16),
      ]),
      h("div", { class: "custom-select-menu" }, items.map((item) => h("button", {
        type: "button",
        class: selectedValues.has(item.value) ? "custom-select-option active" : "custom-select-option",
        "data-value": item.value,
      }, [h("span", {}, item.label), h("span", { class: "multi-check" }, icon("Check", 14))]))),
    ]);
    const trigger = root.querySelector(".custom-select-trigger");
    const hiddenWrap = root.querySelector(".multi-hidden-inputs");
    const label = root.querySelector(".custom-select-label");
    const sync = () => {
      hiddenWrap.innerHTML = "";
      Array.from(selectedValues).forEach((value) => hiddenWrap.appendChild(h("input", { type: "hidden", name: config.name, value })));
      const selectedItems = items.filter((item) => selectedValues.has(item.value));
      if (label) {
        label.textContent = selectedItems.length
          ? selectedItems.length <= 2
            ? selectedItems.map((item) => item.label.replace(/\s+\([^)]*\)$/, "")).join(", ")
            : `${selectedItems.length} members selected`
          : (config.placeholder || "Select");
      }
      root.querySelectorAll(".custom-select-option").forEach((option) => {
        option.classList.toggle("active", selectedValues.has(option.getAttribute("data-value") || ""));
      });
      if (config.onChange) config.onChange(Array.from(selectedValues));
    };
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      document.querySelectorAll(".custom-select.open").forEach((selectEl) => { if (selectEl !== root) selectEl.classList.remove("open"); });
      root.classList.toggle("open");
    });
    root.querySelectorAll(".custom-select-option").forEach((option) => option.addEventListener("click", (event) => {
      event.preventDefault();
      const value = option.getAttribute("data-value") || "";
      if (selectedValues.has(value)) selectedValues.delete(value);
      else selectedValues.add(value);
      sync();
    }));
    root.addEventListener("focusout", () => window.setTimeout(() => {
      if (!root.contains(document.activeElement)) root.classList.remove("open");
    }, 80));
    sync();
    return root;
  }
  function inputWrap(iconName, input, extra) {
    return h("div", { class: "input-wrap" }, [icon(iconName, 17), input, extra || null]);
  }
  function responsiveTable(headers, rows) {
    return h("div", { class: "table-wrap" }, [h("table", {}, [
      h("thead", {}, h("tr", {}, headers.map((head) => h("th", {}, head)))),
      h("tbody", {}, rows.length ? rows.map((row) => h("tr", {}, row.map((cell, i) => h("td", { "data-label": headers[i] }, cell)))) : [h("tr", {}, h("td", { colspan: headers.length }, "No records."))]),
    ])]);
  }
  function badge(text, type) { return h("span", { class: `badge ${type || ""} ${String(text).toLowerCase()}` }, type === "role" ? roleLabel(text) : cap(text)); }
  function logBadge(type) {
    const t = String(type || "activity").toLowerCase();
    const label = t.indexOf("project") >= 0 ? "project" : t.indexOf("chatter") >= 0 ? "chatter" : t.indexOf("message") >= 0 ? "message" : t.indexOf("file") >= 0 || t.indexOf("attachment") >= 0 ? "file" : t.indexOf("login") >= 0 ? "login" : t.indexOf("user") >= 0 ? "user" : t;
    return badge(label);
  }
  function emptyState(text) { return h("div", { class: "empty-state" }, [h("span", {}, [icon("Boxes")]), h("p", {}, text)]); }
  function restricted(text) { return h("article", { class: "card" }, [cardHeader("Restricted", "Your current role cannot access this section."), emptyState(text)]); }
  function userName(id) {
    if (!id) return "";
    const userId = Number(id);
    const pools = [
      state.user ? [state.user] : [],
      state.users,
      state.projects.flatMap((project) => project.members || []),
      state.chatters.flatMap((chatter) => chatter.members || []),
    ];
    for (const pool of pools) {
      const found = pool.find((user) => Number(user.id) === userId);
      if (found) return found.name || found.login || found.email || `User ${id}`;
    }
    return `User ${id}`;
  }
  function projectName(id) { return state.projects.find((p) => p.id === id)?.name || ""; }
  function chatterName(id) { return state.chatters.find((c) => c.id === id)?.name || ""; }
  function projectCustomerNames(project) {
    const customers = (project.members || []).filter(isCustomerUser);
    if (customers.length) return customers.map((user) => user.name || user.login || user.email).join(", ");
    return userName(project.customer_id) || "None";
  }
  function initials(name) { return String(name || "U").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); }
  function cap(value) { return String(value || "").replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()); }
  function formatDate(value) {
    return value ? new Date(value).toLocaleString([], {
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }) : "";
  }
  function messageDayKey(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toDateString();
  }
  function formatMessageTime(value) {
    if (!value) return "";
    return new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  function formatMessageDay(value) {
    if (!value) return "";
    const date = new Date(value);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    if (date.toDateString() === today.toDateString()) return `Today, ${date.toLocaleDateString([], { day: "numeric", month: "long" })}`;
    if (date.toDateString() === yesterday.toDateString()) return `Yesterday, ${date.toLocaleDateString([], { day: "numeric", month: "long" })}`;
    return date.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });
  }
  function hasContactDetails(value) {
    const text = String(value || "");
    return [
      /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/,
      /(\+?\d[\d\s().-]{7,}\d)/,
      /(wa\.me\/\d+|whatsapp\.com\/send\?phone=\d+)/i,
      /((https?:\/\/)?(www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(\/\S*)?)/i,
      /(t\.me\/[a-zA-Z0-9_]+|linkedin\.com\/in\/[a-zA-Z0-9_-]+)/i,
    ].some((pattern) => pattern.test(text));
  }
  function prettyBytes(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let index = 0;
    while (size >= 1024 && index < units.length - 1) { size = size / 1024; index += 1; }
    return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
  }

  window.addEventListener("storage", (event) => {
    if (event.key === "anochat_presence_changed" && apiClient.token() && state.user) {
      refreshPresenceData(true);
    }
  });

  window.addEventListener("anochat_session_expired", (event) => {
    stopPresenceSync();
    stopMessageSync();
    Object.assign(state, {
      user: null, users: [], projects: [], chatters: [], messages: [], notifications: [], files: [], typingUsers: [],
      activityLogs: [], emailLogs: [], stats: null, activeChatter: null, pendingAttachment: null, pendingVoiceDuration: null, replyTo: null, editingMessage: null, editingBody: "", modal: null,
      audioState: {},
      chatInfoExpanded: { members: false, images: false, documents: false },
      lastMessageSignature: "", refreshingMessages: false, lastTypingPingAt: 0, bootstrapping: false, loading: false,
      operations: { tasks: [], documents: [], incidents: [], knowledge: [] },
    });
    toast(event.detail || "Session expired. Please sign in again.", "error");
    render();
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshActiveChatterMessages(true);
  });

  if (apiClient.token()) bootstrap();
  else render();
})();


