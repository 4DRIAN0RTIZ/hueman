(function (root, factory) {
  "use strict";
  const api = factory();
  root.HuemanReleases = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  function slug(text) {
    return String(text).trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  }

  // Parse the git-cliff CHANGELOG into [{ id, version, unreleased, date, groups }].
  function parseChangelog(md) {
    const releases = [];
    let release = null;
    let group = null;
    String(md || "")
      .split(/\r?\n/)
      .forEach((line) => {
        const rel = /^##\s+\[([^\]]+)\](?:\s*-\s*(\S+))?\s*$/.exec(line);
        if (rel) {
          const name = rel[1].trim();
          const unreleased = name.toLowerCase() === "unreleased";
          release = {
            id: slug(name),
            version: unreleased ? null : name,
            unreleased,
            date: rel[2] || null,
            groups: [],
          };
          group = null;
          releases.push(release);
          return;
        }
        if (!release) return;
        const grp = /^###\s+(.+?)\s*$/.exec(line);
        if (grp) {
          group = { title: grp[1], items: [] };
          release.groups.push(group);
          return;
        }
        const item = /^[-*]\s+(.+?)\s*$/.exec(line);
        if (item && group) {
          const m = /^(.*?)\s*\(([0-9a-f]{7,40})\)$/.exec(item[1]);
          group.items.push(m ? { text: m[1], hash: m[2] } : { text: item[1], hash: null });
        }
      });
    return releases;
  }

  function semverParts(v) {
    return String(v)
      .replace(/^v/i, "")
      .split(".")
      .map((n) => parseInt(n, 10) || 0);
  }

  function compareSemver(a, b) {
    const pa = semverParts(a);
    const pb = semverParts(b);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
      const d = (pa[i] || 0) - (pb[i] || 0);
      if (d) return d;
    }
    return 0;
  }

  // version: semver string of the docs being read, or null/undefined for latest (everything).
  function filterReleases(releases, version) {
    if (!version) return releases.slice();
    return releases.filter((r) => !r.unreleased && compareSemver(r.version, version) <= 0);
  }

  function formatDate(iso) {
    if (!iso) return "";
    const raw = String(iso);
    const d = new Date(raw + (/^\d{4}-\d{2}-\d{2}$/.test(raw) ? "T00:00:00Z" : ""));
    if (isNaN(d.getTime())) return raw;
    try {
      return new Intl.DateTimeFormat("es", {
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone: "UTC",
      }).format(d);
    } catch (_) {
      return raw;
    }
  }

  return { parseChangelog, filterReleases, formatDate, compareSemver };
});
