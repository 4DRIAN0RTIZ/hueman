(() => {
  "use strict";

  const STATE = {
    versionsDoc: null,
    versionId: null,
    pageId: null,
    nav: null,
    openNav: false,
    view: "landing",
  };

  const META = {
    landing: {
      title: "hueman: one palette, every tool",
      description:
        "One palette. Every tool. Apply one theme across kitty, nvim, tmux, starship, and whatever you declare — one command.",
    },
    docs: {
      title: "hueman: docs",
      description:
        "One palette. Every tool. Docs for applying one theme across your terminal, editor, prompt, and the rest of your setup.",
    },
  };

  const els = {
    versionSelect: document.getElementById("version-select"),
    sideNav: document.getElementById("side-nav"),
    doc: document.getElementById("doc"),
    pager: document.getElementById("pager"),
    outline: document.getElementById("page-outline"),
    pageStamp: document.getElementById("page-stamp"),
    sectionLabel: document.getElementById("section-label"),
    spineMeta: document.getElementById("spine-meta"),
    heroTitle: document.getElementById("hero-title"),
    heroLead: document.getElementById("hero-lead"),
    heroBadges: document.getElementById("hero-badges"),
    footerVersion: document.getElementById("footer-version"),
    footerUpdated: document.getElementById("footer-updated"),
    heroUpdated: document.getElementById("hero-updated"),
    notice: document.getElementById("version-notice"),
    navToggle: document.getElementById("nav-toggle"),
    backdrop: document.getElementById("nav-backdrop"),
    main: document.getElementById("contenido"),
    progress: document.getElementById("read-progress"),
    masthead: document.getElementById("hero"),
    themes: document.getElementById("themes"),
    landing: document.getElementById("landing"),
    docsShell: document.getElementById("docs-shell"),
    skipLink: document.getElementById("skip-link"),
    brandHome: document.getElementById("brand-home"),
    copyInstall: document.getElementById("copy-install"),
    landingKicker: document.getElementById("landing-kicker"),
    metaDescription: document.getElementById("meta-description"),
    ogTitle: document.getElementById("og-title"),
    ogDescription: document.getElementById("og-description"),
  };

  const Releases = window.HuemanReleases;

  const THEME_KEY = "hueman-docs-theme";

  function applyTheme(name) {
    document.documentElement.setAttribute("data-theme", name);
    els.themes.querySelectorAll("[data-theme-set]").forEach((btn) => {
      btn.setAttribute("aria-checked", String(btn.dataset.themeSet === name));
    });
  }

  function initThemes() {
    applyTheme(document.documentElement.getAttribute("data-theme") || "carbon");
    els.themes.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-theme-set]");
      if (!btn) return;
      applyTheme(btn.dataset.themeSet);
      try {
        localStorage.setItem(THEME_KEY, btn.dataset.themeSet);
      } catch (_) {
        /* storage unavailable: theme applies for this visit only */
      }
    });
  }

  function addCopyButtons() {
    els.doc.querySelectorAll("pre").forEach((pre) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "copy-btn";
      btn.textContent = "copy";
      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText((pre.querySelector("code") || pre).innerText.trimEnd());
          btn.textContent = "copied";
          btn.classList.add("is-done");
          setTimeout(() => {
            btn.textContent = "copy";
            btn.classList.remove("is-done");
          }, 1400);
        } catch (_) {
          btn.textContent = "error";
        }
      });
      pre.appendChild(btn);
    });
  }

  const EXTEND_PAGES = new Set(["add-tool", "add-palette"]);

  function currentVersion() {
    return STATE.versionsDoc.versions.find((v) => v.id === STATE.versionId);
  }

  function pageHref(versionId, pageId) {
    return `?v=${encodeURIComponent(versionId)}&p=${encodeURIComponent(pageId)}`;
  }

  function parseRoute() {
    const params = new URLSearchParams(location.search);
    const defaultVersion = STATE.versionsDoc?.default || "latest";
    let versionId = params.get("v");
    let pageId = params.get("p");
    const hashDocs = location.hash.startsWith("#/");

    // Bare URL (no v/p, no legacy hash) → product landing.
    if (!versionId && !pageId && !hashDocs) {
      return { view: "landing" };
    }

    if (!versionId && hashDocs) {
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
      view: "docs",
      versionId: versionId || defaultVersion,
      pageId: pageId || "intro",
      sectionId: hashDocs ? "" : (location.hash || "").replace(/^#/, ""),
    };
  }

  function setMeta(view, pageTitle) {
    const base = META[view] || META.landing;
    const title =
      view === "docs" && pageTitle ? `${pageTitle} · hueman` : base.title;
    document.title = title;
    if (els.metaDescription) els.metaDescription.setAttribute("content", base.description);
    if (els.ogTitle) els.ogTitle.setAttribute("content", title);
    if (els.ogDescription) els.ogDescription.setAttribute("content", base.description);
  }

  function setView(view) {
    STATE.view = view;
    document.body.dataset.view = view;
    if (els.landing) els.landing.hidden = view !== "landing";
    if (els.docsShell) els.docsShell.hidden = view !== "docs";
    if (els.skipLink) {
      els.skipLink.setAttribute(
        "href",
        view === "landing" ? "#landing-main" : "#contenido"
      );
    }
    if (els.spineMeta) {
      // Landing: wordmark only. Docs: version label (filled in renderHeroAndFooter).
      if (view === "landing") {
        els.spineMeta.textContent = "";
        els.spineMeta.hidden = true;
      } else {
        els.spineMeta.hidden = false;
      }
    }
    if (view === "landing") {
      closeMobileNav();
      if (els.progress) els.progress.style.transform = "scaleX(0)";
      setMeta("landing");
    }
  }

  function goHome({ replace = false } = {}) {
    const next = location.pathname.endsWith("/")
      ? location.pathname
      : location.pathname.replace(/index\.html$/i, "") || "./";
    const url = next || "./";
    if (replace) history.replaceState(null, "", url);
    else history.pushState(null, "", url);
  }

  function setRoute(versionId, pageId, { replace = false } = {}) {
    const url = new URL(location.href);
    url.searchParams.set("v", versionId);
    url.searchParams.set("p", pageId);
    url.hash = "";
    const next = `${url.pathname}${url.search}`;
    if (replace) history.replaceState(null, "", next);
    else history.pushState(null, "", next);
  }

  async function fetchText(path) {
    const res = await fetch(path, { cache: "no-cache" });
    if (!res.ok) throw new Error(`Failed to load ${path} (${res.status})`);
    return res.text();
  }

  async function fetchJson(path) {
    const res = await fetch(path, { cache: "no-cache" });
    if (!res.ok) throw new Error(`Failed to load ${path} (${res.status})`);
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
    if (typeof marked === "undefined") throw new Error("marked.js failed to load");
    const renderer = new marked.Renderer();
    renderer.heading = function heading({ tokens, depth }) {
      const body = this.parser.parseInline(tokens);
      const plain = tokens.map((t) => t.raw || t.text || "").join("");
      const id = slugify(plain);
      if (depth >= 2 && depth <= 3 && id) {
        return (
          `<h${depth} id="${id}">${body}` +
          ` <a class="heading-anchor" href="#${id}" aria-label="Link to this section">#</a>` +
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
    marked.setOptions({ gfm: true, breaks: false, renderer });
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

    if (href.startsWith("#/")) {
      const parts = href.replace(/^#\/?/, "").split("/").filter(Boolean);
      if (parts[0]) {
        return {
          href: pageHref(parts[0], parts[1] || "intro"),
          external: false,
          internal: true,
        };
      }
    }

    return { href, external: false };
  }

  function flatPageIds() {
    if (!STATE.nav) return [];
    return (STATE.nav.sections || []).flatMap((section) =>
      (section.pages || []).filter((id) => STATE.nav.pages[id])
    );
  }

  function currentSectionTitle() {
    if (!STATE.nav) return "Documentation";
    for (const section of STATE.nav.sections || []) {
      if ((section.pages || []).includes(STATE.pageId)) return section.title;
    }
    return "Documentation";
  }

  function versionOptionLabel(v) {
    return v.channel === "latest"
      ? `${v.label} · in development`
      : `${v.label} · released`;
  }

  function renderVersionSelect() {
    const groups = [
      ["Latest", (v) => v.channel === "latest"],
      ["Released", (v) => v.channel !== "latest"],
    ];
    els.versionSelect.innerHTML = groups
      .map(([title, test]) => {
        const options = STATE.versionsDoc.versions
          .filter(test)
          .map((v) => `<option value="${escapeAttr(v.id)}">${escapeAttr(versionOptionLabel(v))}</option>`)
          .join("");
        return options ? `<optgroup label="${title}">${options}</optgroup>` : "";
      })
      .join("");
    els.versionSelect.value = STATE.versionId;
  }

  function renderVersionNotice() {
    const v = currentVersion();
    if (v.channel === "latest") {
      els.notice.innerHTML =
        `<p class="notice notice--dev"><span class="notice__dot" aria-hidden="true"></span>` +
        `Docs in development: tracks the main branch and may describe changes not yet released.</p>`;
      return;
    }
    const latest = STATE.versionsDoc.versions.find((x) => x.channel === "latest");
    const link = latest
      ? ` <a href="${pageHref(latest.id, STATE.pageId)}" data-link>View this page on ${escapeAttr(latest.label)}</a>`
      : "";
    els.notice.innerHTML =
      `<p class="notice notice--old" role="note">` +
      `You are viewing docs for <strong>${escapeAttr(v.label)}</strong> — it may be outdated.${link}</p>`;
  }

  function renderHeroAndFooter() {
    const v = currentVersion();
    const page = STATE.nav?.pages?.[STATE.pageId];
    const pageTitle = page?.title || STATE.pageId;
    const ids = flatPageIds();
    const idx = ids.indexOf(STATE.pageId);
    const sectionTitle = currentSectionTitle();

    els.heroTitle.textContent = pageTitle;
    els.masthead.dataset.num = String(idx >= 0 ? idx + 1 : 0).padStart(2, "0");
    if (els.sectionLabel) els.sectionLabel.textContent = sectionTitle;
    if (els.pageStamp) {
      els.pageStamp.textContent =
        idx >= 0
          ? `page ${String(idx + 1).padStart(2, "0")} / ${String(ids.length).padStart(2, "0")}`
          : `id · ${STATE.pageId}`;
    }
    if (els.spineMeta) els.spineMeta.textContent = v.label;

    if (STATE.pageId === "intro") {
      els.heroLead.textContent =
        "One palette. Every tool. You own the map; one command paints it everywhere.";
    } else if (EXTEND_PAGES.has(STATE.pageId)) {
      els.heroLead.textContent =
        "Add another tool without forking the engine — a template and a target in your config.";
    } else {
      els.heroLead.textContent = `Docs · revision ${v.label}`;
    }

    // One primary version pill; add a channel hint only when it is not redundant
    // (label "latest" + channel "latest" used to render two identical badges).
    const badges = [
      `<span class="badge badge--current" aria-label="Selected version">${escapeAttr(v.label)}</span>`,
    ];
    if (v.channel === "latest") {
      badges.push(`<span class="badge badge--ok">in development</span>`);
    } else if (v.status && v.status !== "current") {
      badges.push(
        `<span class="badge badge--ok">${escapeAttr(v.status)}</span>`
      );
    }
    els.heroBadges.innerHTML = badges.join("");

    const updatedText = Releases.formatDate(v.updated);
    els.heroUpdated.textContent = updatedText;
    els.heroUpdated.setAttribute("datetime", v.updated);
    els.footerVersion.textContent = `rev ${v.label}`;
    els.footerUpdated.textContent = updatedText;
    els.footerUpdated.setAttribute("datetime", v.updated);
    document.title = `${pageTitle} · hueman docs (${v.label})`;
  }

  function renderSideNav() {
    if (!STATE.nav) {
      els.sideNav.innerHTML = "";
      return;
    }

    els.sideNav.innerHTML = (STATE.nav.sections || [])
      .map((section, sectionIdx) => {
        const num = String(sectionIdx + 1).padStart(2, "0");
        const items = (section.pages || [])
          .map((pageId, pageIdx) => {
            const meta = STATE.nav.pages[pageId];
            if (!meta) return "";
            const href = pageHref(STATE.versionId, pageId);
            const current = pageId === STATE.pageId ? ' aria-current="page"' : "";
            const ext = EXTEND_PAGES.has(pageId) ? " is-extend" : "";
            const tick = String(pageIdx + 1).padStart(2, "0");
            return (
              `<li><a href="${href}" data-link class="${ext.trim()}"${current}>` +
              `<span class="ledger__tick">${tick}</span>` +
              `<span class="ledger__label">${meta.title}</span>` +
              `</a></li>`
            );
          })
          .join("");

        return (
          `<section class="ledger__section">` +
          `<header class="ledger__head">` +
          `<span class="ledger__num">${num}</span>` +
          `<h2 class="ledger__title">${section.title}</h2>` +
          `</header>` +
          `<ul class="ledger__list">${items}</ul>` +
          `</section>`
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
      `<span class="pager__dir">Previous</span>` +
      `<span class="pager__title">${prevMeta ? prevMeta.title : ""}</span></a>` +
      `<a class="pager__next" href="${next ? pageHref(STATE.versionId, next) : "#"}" data-link ${next ? "" : "hidden"}>` +
      `<span class="pager__dir">Next</span>` +
      `<span class="pager__title">${nextMeta ? nextMeta.title : ""}</span></a>`;
  }

  function inlineCode(text) {
    return escapeAttr(text).replace(/`([^`]+)`/g, "<code>$1</code>");
  }

  function renderChangelog(md, version) {
    const releases = Releases.filterReleases(Releases.parseChangelog(md), version.semver);
    if (!releases.length) {
      return `<p class="doc__error">No changelog entries for ${escapeAttr(version.label)}.</p>`;
    }
    return releases
      .map((r) => {
        const current = !r.unreleased && r.version === version.semver;
        const title = r.unreleased ? "Unreleased" : `v${escapeAttr(r.version)}`;
        const tag = current
          ? `<span class="release__tag">this version</span>`
          : r.unreleased
            ? `<span class="release__tag release__tag--dev">in development</span>`
            : "";
        const date = r.date
          ? `<time class="release__date" datetime="${escapeAttr(r.date)}">${escapeAttr(Releases.formatDate(r.date))}</time>`
          : "";
        const groups = r.groups
          .map(
            (g) =>
              `<h3 class="release__group">${escapeAttr(g.title)}</h3><ul class="release__items">` +
              g.items
                .map(
                  (i) =>
                    `<li>${inlineCode(i.text)}${i.hash ? ` <code class="chip">${escapeAttr(i.hash)}</code>` : ""}</li>`
                )
                .join("") +
              `</ul>`
          )
          .join("");
        return (
          `<section class="release${current ? " is-current" : ""}">` +
          `<h2 id="${r.id}">${title}${tag}${date}` +
          ` <a class="heading-anchor" href="#${r.id}" aria-label="Link to this section">#</a></h2>` +
          `${groups}</section>`
        );
      })
      .join("");
  }

  function renderOutline() {
    if (!els.outline) return;
    const headings = [...els.doc.querySelectorAll("h2[id], h3[id]")];
    if (!headings.length) {
      els.outline.innerHTML = `<p class="outline__empty">No sections</p>`;
      return;
    }
    els.outline.innerHTML = headings
      .map((h) => {
        const depth = h.tagName === "H3" ? " outline__h3" : "";
        return `<a class="outline__link${depth}" href="#${h.id}">${h.childNodes[0]?.textContent?.trim() || h.id}</a>`;
      })
      .join("");
  }

  function updateProgress() {
    if (STATE.view !== "docs" || !els.progress) return;
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const ratio = max > 0 ? window.scrollY / max : 0;
    els.progress.style.transform = `scaleX(${Math.min(1, Math.max(0, ratio))})`;

    if (!els.outline) return;
    const headings = [...els.doc.querySelectorAll("h2[id], h3[id]")];
    let active = null;
    for (const h of headings) {
      if (h.getBoundingClientRect().top <= 120) active = h.id;
    }
    els.outline.querySelectorAll("a").forEach((a) => {
      a.classList.toggle("is-active", a.getAttribute("href") === `#${active}`);
    });
  }

  function closeMobileNav() {
    STATE.openNav = false;
    document.body.classList.remove("is-nav-open");
    els.navToggle.setAttribute("aria-expanded", "false");
    els.navToggle.setAttribute("aria-label", "Open index");
    els.backdrop.hidden = true;
  }

  function openMobileNav() {
    STATE.openNav = true;
    document.body.classList.add("is-nav-open");
    els.navToggle.setAttribute("aria-expanded", "true");
    els.navToggle.setAttribute("aria-label", "Close index");
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
    if (el) el.scrollIntoView({ block: "start" });
  }

  async function loadPage(sectionId) {
    const version = currentVersion();
    const page = STATE.nav.pages[STATE.pageId];
    els.doc.setAttribute("aria-busy", "true");
    els.doc.innerHTML = `<p class="doc__loading">Loading…</p>`;

    if (!page) {
      els.doc.innerHTML = `<p class="doc__error">Unknown page: <code>${STATE.pageId}</code></p>`;
      els.doc.setAttribute("aria-busy", "false");
      renderOutline();
      return;
    }

    try {
      if (page.derived || page.file === null) {
        const md = await fetchText("data/changelog.md");
        els.doc.innerHTML = renderChangelog(md, version);
      } else {
        const base = version.contentDir.replace(/\/?$/, "");
        const md = await fetchText(`${base}/${page.file}`);
        els.doc.innerHTML = marked.parse(md);
        const first = els.doc.firstElementChild;
        if (first && first.tagName === "H1") first.remove();
      }
      els.doc.setAttribute("aria-busy", "false");
      addCopyButtons();
      renderOutline();

      if (sectionId) requestAnimationFrame(() => scrollToSection(sectionId));
      else {
        if (window.matchMedia("(max-width: 900px)").matches) {
          els.main.focus({ preventScroll: true });
        }
        window.scrollTo({ top: 0 });
      }
    } catch (err) {
      els.doc.innerHTML = `<p class="doc__error">${err.message}</p>`;
      els.doc.setAttribute("aria-busy", "false");
      renderOutline();
    }
  }

  async function applyRoute() {
    const parsed = parseRoute();

    if (parsed.view === "landing") {
      setView("landing");
      // Keep the address bar clean (drop stray hash / empty search).
      if (location.search || location.hash) {
        goHome({ replace: true });
      }
      return;
    }

    setView("docs");

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
      if (!STATE.nav.pages[STATE.pageId]) STATE.pageId = "intro";
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
    renderVersionNotice();
    renderPager();
    setMeta("docs", STATE.nav?.pages?.[STATE.pageId]?.title);

    const mustReload =
      prevVersion !== STATE.versionId ||
      prevPage !== STATE.pageId ||
      els.doc.dataset.page !== STATE.pageId;

    if (mustReload) {
      await loadPage(parsed.sectionId);
      els.doc.dataset.page = STATE.pageId;
    } else if (parsed.sectionId) {
      scrollToSection(parsed.sectionId);
    }

    closeMobileNav();
    updateProgress();
  }

  function onDocumentClick(event) {
    const home = event.target.closest("#brand-home, #colophon-home");
    if (home) {
      event.preventDefault();
      goHome();
      applyRoute().catch(showRouteError);
      return;
    }

    const link = event.target.closest("a[data-link]");
    if (!link) return;
    const href = link.getAttribute("href") || "";
    if (!href.startsWith("?") && !href.startsWith("#/")) return;
    event.preventDefault();

    let versionId = STATE.versionId || STATE.versionsDoc?.default || "latest";
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
    setRoute(versionId, pageId);
    applyRoute().catch(showRouteError);
  }

  function showRouteError(err) {
    setView("docs");
    if (els.doc) {
      els.doc.innerHTML = `<p class="doc__error">${err.message}</p>`;
    }
  }

  function initLandingActions() {
    if (!els.copyInstall) return;
    els.copyInstall.addEventListener("click", async () => {
      const text = els.copyInstall.dataset.copy || "pipx install hueman-cli";
      try {
        await navigator.clipboard.writeText(text);
        els.copyInstall.textContent = "copied";
        els.copyInstall.classList.add("is-done");
        setTimeout(() => {
          els.copyInstall.textContent = "copy";
          els.copyInstall.classList.remove("is-done");
        }, 1400);
      } catch (_) {
        els.copyInstall.textContent = "error";
      }
    });
  }

  function cmpSemver(a, b) {
    const pa = String(a).split(".").map((n) => parseInt(n, 10) || 0);
    const pb = String(b).split(".").map((n) => parseInt(n, 10) || 0);
    const len = Math.max(pa.length, pb.length);
    for (let i = 0; i < len; i++) {
      const d = (pa[i] || 0) - (pb[i] || 0);
      if (d) return d;
    }
    return 0;
  }

  function formatReleaseLabel(version) {
    if (!version) return null;
    const v = String(version).trim();
    return v.startsWith("v") ? v : `v${v}`;
  }

  function latestReleaseFromVersions() {
    const releases = (STATE.versionsDoc?.versions || [])
      .filter((v) => v.channel === "release" && v.semver)
      .sort((a, b) => cmpSemver(b.semver, a.semver));
    if (!releases.length) return null;
    return formatReleaseLabel(releases[0].label || releases[0].semver);
  }

  async function latestReleaseLabel() {
    // Prefer CHANGELOG (tracks every cut, even without a frozen docs snapshot).
    try {
      const md = await fetchText("data/changelog.md");
      const cut = (Releases.parseChangelog(md) || []).find(
        (r) => !r.unreleased && r.version
      );
      if (cut) return formatReleaseLabel(cut.version);
    } catch (_) {
      /* fall through */
    }
    return latestReleaseFromVersions();
  }

  async function fillLandingKicker() {
    if (!els.landingKicker) return;
    const release = await latestReleaseLabel();
    els.landingKicker.textContent = release
      ? `MIT · open source · ${release}`
      : "MIT · open source";
  }

  async function boot() {
    try {
      initThemes();
      initLandingActions();
      configureMarked();
      STATE.versionsDoc = await fetchJson("data/versions.json");
      fillLandingKicker().catch(() => {});
      const parsed = parseRoute();
      if (parsed.view === "docs") {
        STATE.versionId = parsed.versionId;
        STATE.pageId = parsed.pageId;
      } else {
        STATE.versionId = STATE.versionsDoc.default || "latest";
        STATE.pageId = null;
      }

      els.versionSelect.addEventListener("change", () => {
        setRoute(els.versionSelect.value, STATE.pageId || "intro");
        applyRoute().catch(showRouteError);
      });
      els.navToggle.addEventListener("click", toggleMobileNav);
      els.backdrop.addEventListener("click", closeMobileNav);
      document.addEventListener("click", onDocumentClick);
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && STATE.openNav) closeMobileNav();
      });
      window.addEventListener("scroll", updateProgress, { passive: true });
      window.addEventListener("popstate", () => {
        applyRoute().catch(showRouteError);
      });

      await applyRoute();
    } catch (err) {
      setView("docs");
      els.doc.innerHTML =
        `<p class="doc__error">${err.message}</p>` +
        `<p class="doc__error">Serve <code>website/</code> over HTTP ` +
        `(e.g. <code>python3 -m http.server 8765 --directory website</code>).</p>`;
    }
  }

  boot();
})();
