(() => {
  "use strict";

  const STATE = {
    versionsDoc: null,
    versionId: null,
    pageId: null,
    nav: null,
    openNav: false,
  };

  const els = {
    versionSelect: document.getElementById("version-select"),
    sideNav: document.getElementById("side-nav"),
    doc: document.getElementById("doc"),
    pager: document.getElementById("pager"),
    heroTitle: document.getElementById("hero-title"),
    heroLead: document.getElementById("hero-lead"),
    heroBadges: document.getElementById("hero-badges"),
    footerVersion: document.getElementById("footer-version"),
    footerUpdated: document.getElementById("footer-updated"),
    navToggle: document.getElementById("nav-toggle"),
    backdrop: document.getElementById("nav-backdrop"),
    main: document.getElementById("contenido"),
    progress: document.getElementById("read-progress"),
  };

  const EXTEND_PAGES = new Set(["add-tool", "add-palette"]);

  function currentVersion() {
    return STATE.versionsDoc.versions.find((v) => v.id === STATE.versionId);
  }

  function pageHref(versionId, pageId) {
    const v = encodeURIComponent(versionId);
    const p = encodeURIComponent(pageId);
    return `?v=${v}&p=${p}`;
  }

  function parseRoute() {
    const params = new URLSearchParams(location.search);
    const defaultVersion = STATE.versionsDoc?.default || "latest";
    let versionId = params.get("v");
    let pageId = params.get("p");

    // Legacy hash routes: #/latest/add-tool
    if (!versionId && location.hash.startsWith("#/")) {
      const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
      const known = new Set((STATE.versionsDoc?.versions || []).map((x) => x.id));
      if (parts.length && known.has(parts[0])) {
        versionId = parts[0];
        pageId = parts[1] || "intro";
      } else if (parts.length) {
        versionId = defaultVersion;
        pageId = parts[0];
      }
    }

    return {
      versionId: versionId || defaultVersion,
      pageId: pageId || "intro",
      sectionId: location.hash.startsWith("#/") ? "" : (location.hash || "").replace(/^#/, ""),
    };
  }

  function setRoute(versionId, pageId, { replace = false, keepSection = false } = {}) {
    const url = new URL(location.href);
    url.searchParams.set("v", versionId);
    url.searchParams.set("p", pageId);
    if (!keepSection) {
      url.hash = "";
    }
    const next = `${url.pathname}${url.search}${url.hash}`;
    if (replace) {
      history.replaceState(null, "", next);
    } else {
      history.pushState(null, "", next);
    }
  }

  async function fetchText(path) {
    const res = await fetch(path, { cache: "no-cache" });
    if (!res.ok) {
      throw new Error(`No se pudo cargar ${path} (${res.status})`);
    }
    return res.text();
  }

  async function fetchJson(path) {
    const res = await fetch(path, { cache: "no-cache" });
    if (!res.ok) {
      throw new Error(`No se pudo cargar ${path} (${res.status})`);
    }
    return res.json();
  }

  function slugify(text) {
    return String(text)
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-");
  }

  function escapeAttr(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function configureMarked() {
    if (typeof marked === "undefined") {
      throw new Error("marked.js no cargó");
    }
    const renderer = new marked.Renderer();
    renderer.heading = function heading({ tokens, depth }) {
      const body = this.parser.parseInline(tokens);
      const plain = tokens.map((t) => t.raw || t.text || "").join("");
      const id = slugify(plain);
      if (depth >= 2 && depth <= 3 && id) {
        return (
          `<h${depth} id="${id}">` +
          `${body}` +
          ` <a class="heading-anchor" href="#${id}" aria-label="Enlace a esta sección">#</a>` +
          `</h${depth}>\n`
        );
      }
      return `<h${depth}>${body}</h${depth}>\n`;
    };
    renderer.link = function link({ href, title, tokens }) {
      const text = this.parser.parseInline(tokens);
      const titleAttr = title ? ` title="${escapeAttr(title)}"` : "";
      const mapped = mapDocHref(href);
      if (mapped.external) {
        return `<a href="${escapeAttr(mapped.href)}"${titleAttr} rel="noopener noreferrer" target="_blank">${text}</a>`;
      }
      const attr = mapped.internal ? " data-link" : "";
      return `<a href="${escapeAttr(mapped.href)}"${titleAttr}${attr}>${text}</a>`;
    };
    marked.setOptions({
      gfm: true,
      breaks: false,
      renderer,
    });
  }

  function mapDocHref(href) {
    if (!href) return { href: "#", external: false };
    if (
      /^(https?:|mailto:|tel:)/i.test(href) ||
      href.startsWith("//") ||
      href.startsWith("data:")
    ) {
      return { href, external: true };
    }
    if (href.startsWith("#") && !href.startsWith("#/")) {
      return { href, external: false };
    }

    let path = href.split("#")[0].replace(/\\/g, "/");
    const segments = [];
    for (const part of path.split("/")) {
      if (!part || part === ".") continue;
      if (part === "..") {
        segments.pop();
        continue;
      }
      segments.push(part);
    }
    path = segments.join("/");

    if (path.endsWith(".md")) {
      const pages = Object.entries(STATE.nav?.pages || {});
      const entry =
        pages.find(([, meta]) => meta.file === path) ||
        pages.find(
          ([, meta]) =>
            meta.file && meta.file.split("/").pop() === path.split("/").pop()
        );
      if (entry) {
        return {
          href: pageHref(STATE.versionId, entry[0]),
          external: false,
          internal: true,
          pageId: entry[0],
        };
      }
    }

    // Legacy hash app links
    if (href.startsWith("#/")) {
      const parts = href.replace(/^#\/?/, "").split("/").filter(Boolean);
      if (parts[0]) {
        const v = parts[0];
        const p = parts[1] || "intro";
        return { href: pageHref(v, p), external: false, internal: true, pageId: p };
      }
    }

    return { href, external: false };
  }

  function renderVersionSelect() {
    const versions = STATE.versionsDoc.versions;
    els.versionSelect.innerHTML = versions
      .map((v) => {
        const label = v.channel === "latest" ? `${v.label} (tip)` : v.label;
        return `<option value="${v.id}">${label}</option>`;
      })
      .join("");
    els.versionSelect.value = STATE.versionId;
  }

  function renderHeroAndFooter() {
    const v = currentVersion();
    const page = STATE.nav?.pages?.[STATE.pageId];
    const pageTitle = page?.title || STATE.pageId;
    els.heroTitle.textContent = pageTitle;
    if (STATE.pageId === "intro") {
      els.heroLead.textContent =
        "Una paleta YAML, templates Jinja y targets declarativos para themear tus tools — incluida la tuya.";
    } else if (EXTEND_PAGES.has(STATE.pageId)) {
      els.heroLead.textContent =
        "Extiende hueman sin tocar el motor: un template Jinja y un target en tu config bastan.";
    } else {
      els.heroLead.textContent = `Documentación de hueman · ${v.label}`;
    }

    const channelLabel =
      v.channel === "latest" ? "latest" : v.status || v.channel || "release";
    els.heroBadges.innerHTML = [
      `<span class="badge badge--accent">${v.label}</span>`,
      `<span class="badge badge--ok">${channelLabel}</span>`,
      v.semver ? `<span class="badge">semver ${v.semver}</span>` : "",
      `<span class="badge">actualizado ${v.updated}</span>`,
    ]
      .filter(Boolean)
      .join("");

    els.footerVersion.textContent = `Docs ${v.label}`;
    els.footerUpdated.textContent = v.updated;
    els.footerUpdated.setAttribute("datetime", v.updated);
    document.title = `${pageTitle} · hueman docs (${v.label})`;
  }

  function flatPageIds() {
    if (!STATE.nav) return [];
    return (STATE.nav.sections || []).flatMap((section) =>
      (section.pages || []).filter((id) => STATE.nav.pages[id])
    );
  }

  function renderSideNav() {
    if (!STATE.nav) {
      els.sideNav.innerHTML = "";
      return;
    }
    els.sideNav.innerHTML = (STATE.nav.sections || [])
      .map((section) => {
        const items = (section.pages || [])
          .map((pageId) => {
            const meta = STATE.nav.pages[pageId];
            if (!meta) return "";
            const href = pageHref(STATE.versionId, pageId);
            const current = pageId === STATE.pageId ? ' aria-current="page"' : "";
            const ext = EXTEND_PAGES.has(pageId) ? " is-extend" : "";
            return (
              `<li><a href="${href}" data-link class="${ext.trim()}"${current}>` +
              `${meta.title}</a></li>`
            );
          })
          .join("");
        return (
          `<div class="side-nav__section">` +
          `<p class="side-nav__section-title">${section.title}</p>` +
          `<ul class="side-nav__list">${items}</ul>` +
          `</div>`
        );
      })
      .join("");
  }

  function renderPager() {
    if (!els.pager || !STATE.nav) {
      if (els.pager) els.pager.innerHTML = "";
      return;
    }
    const ids = flatPageIds();
    const idx = ids.indexOf(STATE.pageId);
    const prev = idx > 0 ? ids[idx - 1] : null;
    const next = idx >= 0 && idx < ids.length - 1 ? ids[idx + 1] : null;
    const prevMeta = prev ? STATE.nav.pages[prev] : null;
    const nextMeta = next ? STATE.nav.pages[next] : null;

    els.pager.innerHTML =
      `<a class="pager__prev" href="${prev ? pageHref(STATE.versionId, prev) : "#"}" data-link ${prev ? "" : "hidden"}>` +
      `<span class="pager__dir">Anterior</span>` +
      `<span class="pager__title">${prevMeta ? prevMeta.title : ""}</span></a>` +
      `<a class="pager__next" href="${next ? pageHref(STATE.versionId, next) : "#"}" data-link ${next ? "" : "hidden"}>` +
      `<span class="pager__dir">Siguiente</span>` +
      `<span class="pager__title">${nextMeta ? nextMeta.title : ""}</span></a>`;
  }

  function updateProgress() {
    if (!els.progress) return;
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const ratio = max > 0 ? window.scrollY / max : 0;
    els.progress.style.width = `${Math.min(100, Math.max(0, ratio * 100))}%`;
  }

  function closeMobileNav() {
    STATE.openNav = false;
    document.body.classList.remove("is-nav-open");
    els.navToggle.setAttribute("aria-expanded", "false");
    els.navToggle.setAttribute("aria-label", "Abrir menú de navegación");
    els.backdrop.hidden = true;
  }

  function openMobileNav() {
    STATE.openNav = true;
    document.body.classList.add("is-nav-open");
    els.navToggle.setAttribute("aria-expanded", "true");
    els.navToggle.setAttribute("aria-label", "Cerrar menú de navegación");
    els.backdrop.hidden = false;
  }

  function toggleMobileNav() {
    if (STATE.openNav) closeMobileNav();
    else openMobileNav();
  }

  async function loadNav(version) {
    const base = version.contentDir.replace(/\/?$/, "");
    STATE.nav = await fetchJson(`${base}/nav.json`);
  }

  function scrollToSection(sectionId) {
    if (!sectionId) return;
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ block: "start" });
    }
  }

  async function loadPage(sectionId) {
    const version = currentVersion();
    const page = STATE.nav.pages[STATE.pageId];
    els.doc.setAttribute("aria-busy", "true");
    els.doc.innerHTML = `<p class="doc__loading">Cargando…</p>`;

    if (!page) {
      els.doc.innerHTML = `<p class="doc__error">Página desconocida: <code>${STATE.pageId}</code></p>`;
      els.doc.setAttribute("aria-busy", "false");
      return;
    }

    try {
      let md;
      if (page.derived || page.file === null) {
        md = await fetchText("data/changelog.md");
      } else {
        const base = version.contentDir.replace(/\/?$/, "");
        md = await fetchText(`${base}/${page.file}`);
      }

      els.doc.innerHTML = marked.parse(md);
      const first = els.doc.firstElementChild;
      if (first && first.tagName === "H1") {
        first.remove();
      }
      els.doc.setAttribute("aria-busy", "false");

      if (sectionId) {
        requestAnimationFrame(() => scrollToSection(sectionId));
      } else if (window.matchMedia("(max-width: 920px)").matches) {
        els.main.focus({ preventScroll: true });
        window.scrollTo({ top: 0 });
      } else {
        window.scrollTo({ top: 0 });
      }
    } catch (err) {
      els.doc.innerHTML = `<p class="doc__error">${err.message}</p>`;
      els.doc.setAttribute("aria-busy", "false");
    }
  }

  async function applyRoute() {
    const parsed = parseRoute();
    const knownVersions = new Set(STATE.versionsDoc.versions.map((v) => v.id));
    if (!knownVersions.has(parsed.versionId)) {
      parsed.versionId = STATE.versionsDoc.default;
    }

    const prevVersion = STATE.versionId;
    const prevPage = STATE.pageId;
    STATE.versionId = parsed.versionId;
    STATE.pageId = parsed.pageId;

    if (prevVersion !== STATE.versionId || !STATE.nav) {
      await loadNav(currentVersion());
      if (!STATE.nav.pages[STATE.pageId]) {
        STATE.pageId = "intro";
      }
    }

    const expected = pageHref(STATE.versionId, STATE.pageId);
    const params = new URLSearchParams(location.search);
    const searchMatches =
      params.get("v") === STATE.versionId && params.get("p") === STATE.pageId;
    const legacyHash = location.hash.startsWith("#/");
    if (!searchMatches || legacyHash) {
      const section =
        !legacyHash && parsed.sectionId ? `#${parsed.sectionId}` : "";
      history.replaceState(null, "", `${expected}${section}`);
    }

    renderVersionSelect();
    renderSideNav();
    renderHeroAndFooter();
    renderPager();

    const mustReload =
      prevVersion !== STATE.versionId ||
      prevPage !== STATE.pageId ||
      els.doc.dataset.page !== STATE.pageId;
    if (mustReload) {
      await loadPage(parsed.sectionId);
      els.doc.dataset.page = STATE.pageId;
      requestAnimationFrame(updateProgress);
    } else if (parsed.sectionId) {
      scrollToSection(parsed.sectionId);
    }

    closeMobileNav();
    updateProgress();
  }

  function onDocumentClick(event) {
    const link = event.target.closest("a[data-link]");
    if (!link) return;
    const href = link.getAttribute("href") || "";
    if (!href.startsWith("?") && !href.startsWith("#/")) return;
    event.preventDefault();

    let versionId = STATE.versionId;
    let pageId = "intro";
    if (href.startsWith("?")) {
      const params = new URLSearchParams(href.replace(/^\?/, "").split("#")[0]);
      versionId = params.get("v") || versionId;
      pageId = params.get("p") || "intro";
    } else {
      const parts = href.replace(/^#\/?/, "").split("/").filter(Boolean);
      versionId = parts[0] || versionId;
      pageId = parts[1] || "intro";
    }
    setRoute(versionId, pageId, { replace: false });
    applyRoute().catch((err) => {
      els.doc.innerHTML = `<p class="doc__error">${err.message}</p>`;
    });
  }

  async function boot() {
    try {
      configureMarked();
      STATE.versionsDoc = await fetchJson("data/versions.json");

      const parsed = parseRoute();
      STATE.versionId = parsed.versionId;
      STATE.pageId = parsed.pageId;

      els.versionSelect.addEventListener("change", () => {
        setRoute(els.versionSelect.value, STATE.pageId || "intro", {
          replace: false,
        });
        applyRoute().catch((err) => {
          els.doc.innerHTML = `<p class="doc__error">${err.message}</p>`;
        });
      });
      els.navToggle.addEventListener("click", toggleMobileNav);
      els.backdrop.addEventListener("click", closeMobileNav);
      document.addEventListener("click", onDocumentClick);
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && STATE.openNav) closeMobileNav();
      });
      window.addEventListener("scroll", updateProgress, { passive: true });
      window.addEventListener("popstate", () => {
        applyRoute().catch((err) => {
          els.doc.innerHTML = `<p class="doc__error">${err.message}</p>`;
        });
      });

      await applyRoute();
    } catch (err) {
      els.doc.innerHTML =
        `<p class="doc__error">${err.message}</p>` +
        `<p class="doc__error">Sirve la carpeta <code>website/</code> por HTTP ` +
        `(por ejemplo <code>python3 -m http.server 8765 --directory website</code>).</p>`;
    }
  }

  boot();
})();
