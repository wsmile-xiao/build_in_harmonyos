# DRAFT-kirigami-6-18-0-qml-theme-resource-staging

Kirigami's Qt Quick icon test needs the upstream KDE Desktop theme at the
build-tree path it resolves during CTest. A normal QML import path only makes
installed modules visible and does not provide that test input. Stage the exact
upstream `Theme.qml` before CTest, preserving `tst_icon.qml` coverage; exclude
only the separately unsupported desktop-theme case with its specific OHOS
runtime reason.

## Identity and conclusion

| Field | Value |
|---|---|
| Status | Historical target evidence pending review |
| Proposed route | Follow-up knowledge PR for an already merged adaptation |
| Contributor | zxyAtom |
| Source PR | !7443, merged 2026-09-04 |
| Source commit | `15ecf61916a821514f97015576678e00f5d86f8c` |
| Delivery PR | To be created from current `main` |
| Package | kirigami/6.18.0 |
| Upstream | `v6.18.0`; `https://invent.kde.org/frameworks/kirigami` |

The historical CI result proves that the source commit staged
`src/styles/org.kde.desktop/Theme.qml` to
`build/bin/org/kde/kirigami/Theme.qml`, then ran 35 of 36 original Qt Quick
tests and one installed-package API consumer. It does not prove that the OHOS
runner supplies a complete KDE Desktop style plugin or the font data required
by `tst_theme.qml`.

## Extraction from merged PR #7443

| Source fact | Reusable mechanism | This extraction adds |
|---|---|---|
| `_prepare_upstream_test_theme()` copies the fixed upstream QML file into the CTest resource path before `ctest`. | A QML import path is not a substitute for test data resolved from a build-tree resource path. | The exact source-to-target contract and the narrow test-preservation rule. |
| `tst_icon.qml` remains in the upstream suite after staging. | Supply the missing fixture before excluding a test. | A negative rule against hiding the icon-test regression. |
| CI #37386 reports 35/36 upstream Qt Quick tests and the Kirigami Units/IconSizes consumer `1/1`. | Keep upstream-suite and installed-consumer denominators separate. | Explicit historical evidence and test accounting. |

Original contribution: merged PR #7443 added the Kirigami recipe, its runtime
environment, upstream Qt Quick test execution, and an API-reaching consumer.
This follow-up contributes only the paired knowledge drafts. It does not modify
the merged package or claim a new target run.

## Trigger, cause, and repair

The trigger is an OHOS Kirigami build with `BUILD_TESTING=ON`, where
`tst_icon.qml` requests the KDE Desktop theme from
`build/bin/org/kde/kirigami/Theme.qml`. The source file instead lives at
`src/styles/org.kde.desktop/Theme.qml`; QML module imports do not materialize it
at the test's build-tree location.

Before running CTest, require the source file to exist and copy it with
`shutil.copy2` to the requested build-tree destination. The recipe then runs
the original suite. It excludes only `tst_theme.qml` on OHOS because the runner
lacks the Basic-style Kirigami platform plugin and font data, causing KDE
Desktop color expectations to fall back to Qt Basic values.

Do not solve this by disabling `BUILD_TESTING` or adding `tst_icon.qml` to the
exclusion list. Those changes avoid the fixture contract rather than verifying
it. Re-check both source and target paths when upgrading Kirigami or changing
the upstream test layout.

## Evidence matrix

| ID | Type | Input and command | Result |
|---|---|---|---|
| EVID-01 | static | `conanfile.py` at source commit, `_prepare_upstream_test_theme()`. | Copies the exact upstream theme to the CTest lookup path and fails clearly if the source fixture is absent. |
| EVID-02 | historical | OHOS CI #37386, `conan create archives/k/kirigami/6.18.0 -pr:h ohos-aarch64`. | L0/L1/L4/L5 passed; original Qt Quick tests passed `35/36`. |
| EVID-03 | historical | The same CI's `test_kirigami` consumer. | Kirigami Platform Units properties and IconSizes invokable contract passed `1/1`. |

The original PR body records the sole unexecuted test as `tst_theme.qml`; it is
not counted as a pass. The historical run is tied to source commit
`15ecf61916a821514f97015576678e00f5d86f8c`. This follow-up changes only
knowledge files, so it does not represent a new current-main target execution.

## Test accounting

| Scope | Inventory | Pass | Fail | Skip | Not executed | Basis |
|---|---:|---:|---:|---:|---:|---|
| Upstream Kirigami Qt Quick tests | 36 | 35 | 0 | 1 | 0 | Historical OHOS CI #37386; only `tst_theme.qml` is excluded for the documented desktop-plugin/font limit. |
| Installed Kirigami Units/IconSizes consumer | 1 | 1 | 0 | 0 | 0 | Historical OHOS CI #37386. |

The consumer test does not increase the upstream `35/36` count.

## Relation to existing knowledge

E294 restores complete upstream tests through a second static build tree; it
does not cover a fixture missing from a test's resource lookup path. Existing
E330, E383, and E537 cover OHOS SONAME handling and absolute `DT_NEEDED`
repair. They are not repeated here. This draft instead covers the orthogonal
Qt Quick testing contract: a source QML fixture must be staged at the
build-tree path requested by CTest, and the affected icon test should stay
enabled after doing so.

Search scope: `knowledge/drafts`, `knowledge/doc`, and `knowledge/graph` for
`Kirigami`, `Theme.qml`, `tst_icon.qml`, `QML`, and `resource staging`. No
existing package-specific QML fixture-staging entry was found. This is a
follow-up extraction from merged PR #7443, not an in-place PR upgrade.

## Source index and self-check

- Source implementation: `archives/k/kirigami/6.18.0/conanfile.py` at
  `15ecf61916a821514f97015576678e00f5d86f8c`, especially
  `_prepare_upstream_test_theme()`.
- Source validation: merged PR !7443, OHOS CI #37386.
- Consumer: `archives/k/kirigami/6.18.0/test_package/test_kirigami.cpp` at the
  same source commit.
- Delivery shape: a new knowledge-only branch from current `main`, following
  the merged-source supplement pattern of PR #8217.

The KV and Markdown share one ID and `doc_file`. The draft remains subject to
similarity review and normal PR review; its conclusions are deliberately
limited to the recorded Kirigami 6.18.0 test layout and OHOS CI environment.
