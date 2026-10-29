"use strict";
const test = require("node:test");
const assert = require("node:assert");
const R = require("../assets/js/releases.js");

const MD = [
  "# Changelog",
  "",
  "All notable changes.",
  "",
  "## [Unreleased]",
  "",
  "### Bug Fixes",
  "",
  "- Package colors (e6d0a6a)",
  "",
  "## [0.2.0] - 2026-11-01",
  "",
  "### Features",
  "",
  "- Add thing (abc1234)",
  "- No hash here",
  "",
  "## [0.1.0] - 2026-10-16",
  "",
  "### Bug Fixes",
  "",
  "- Fix a (a669a55)",
  "",
  "### Build",
  "",
  "- Add cliff (5edf624)",
  "",
].join("\n");

test("parseChangelog splits releases in document order", () => {
  const r = R.parseChangelog(MD);
  assert.deepStrictEqual(r.map((x) => x.id), ["unreleased", "0-2-0", "0-1-0"]);
  assert.strictEqual(r[0].unreleased, true);
  assert.strictEqual(r[0].version, null);
  assert.strictEqual(r[0].date, null);
  assert.strictEqual(r[2].version, "0.1.0");
  assert.strictEqual(r[2].date, "2026-10-16");
});

test("parseChangelog groups and items with trailing hash", () => {
  const r = R.parseChangelog(MD);
  assert.deepStrictEqual(r[2].groups.map((g) => g.title), ["Bug Fixes", "Build"]);
  assert.deepStrictEqual(r[2].groups[0].items, [{ text: "Fix a", hash: "a669a55" }]);
  assert.deepStrictEqual(r[1].groups[0].items[1], { text: "No hash here", hash: null });
});

test("parseChangelog ignores preamble and handles empty input", () => {
  assert.deepStrictEqual(R.parseChangelog(""), []);
  assert.deepStrictEqual(R.parseChangelog("# Changelog\n\nintro"), []);
  assert.deepStrictEqual(R.parseChangelog(null), []);
});

test("filterReleases for latest (null) keeps everything", () => {
  const r = R.parseChangelog(MD);
  assert.strictEqual(R.filterReleases(r, null).length, 3);
});

test("filterReleases drops Unreleased and newer versions", () => {
  const r = R.parseChangelog(MD);
  assert.deepStrictEqual(R.filterReleases(r, "0.1.0").map((x) => x.id), ["0-1-0"]);
  assert.deepStrictEqual(
    R.filterReleases(r, "0.2.0").map((x) => x.id),
    ["0-2-0", "0-1-0"]
  );
});

test("filterReleases compares numerically, not lexically", () => {
  const rel = [
    { id: "0-10-0", version: "0.10.0", unreleased: false },
    { id: "0-9-0", version: "0.9.0", unreleased: false },
  ];
  assert.deepStrictEqual(R.filterReleases(rel, "0.9.0").map((x) => x.id), ["0-9-0"]);
});

test("formatDate renders long English date", () => {
  const out = R.formatDate("2026-10-16");
  assert.match(out, /16/);
  assert.match(out, /October/i);
  assert.match(out, /2026/);
});

test("formatDate falls back to raw input when invalid", () => {
  assert.strictEqual(R.formatDate("nope"), "nope");
  assert.strictEqual(R.formatDate(""), "");
  assert.strictEqual(R.formatDate(null), "");
});
