# libkcddb 26.04.3 notes

## Scope

KDE Gear 26.04.3 CDDB library (CD audio metadata query/submit/cache) — the
direct dependency prerequisite of the audiocd KIO-slave (platform task
#6853, dependency activity of audiocd #3888). Provides libKCddb6.so.

## Why this is a dependency-chain task

audiocd (26.04.3) links KCddb for CD metadata lookups. kio/kcmutils/solid
are NOT published to the ohpcd registry, so upstream's KIO-based HTTP
transport and the KCM settings module cannot be used as-is.

## OHOS adaptation summary

### 1. KIO -> Qt6::Network transport replacement

Upstream uses KIO only for plain HTTP:
- `KIO::get(url, NoReload, HideProgressInfo)` in asynchttplookup /
  synchttplookup / sites (HTTP GET)
- `KIO::http_post(url, data, HideProgressInfo)` + `addMetaData("customHTTPHeader", ...)`
  in httpsubmit (HTTP POST with custom headers)

Replacement design (public API unchanged — Lookup/Submit/Sites classes keep
their signatures):

| upstream (KIO) | replacement (Qt6::Network) |
|---|---|
| `KIO::TransferJob* job = KIO::get(url, ...)` | `QNetworkAccessManager *nam = new QNetworkAccessManager(this); QNetworkReply *job = nam->get(QNetworkRequest(url));` |
| `KIO::http_post` + `addMetaData(content-type)` | `nam->post(request, body)` with `request.setHeader(ContentTypeHeader, "text/plain")` |
| `addMetaData(customHTTPHeader, header)` | `request.setRawHeader(...)` per header (Category/Discid/User-Email/Submit-Mode/Charset) |
| `TransferJob::data` signal -> slotData chunks | dropped; full body via `job->readAll()` after finished |
| `KJob::result` signal -> slotResult(KJob*) | `QNetworkReply::finished` -> slotResult() + `qobject_cast<QNetworkReply*>(sender())` |
| `job->exec()` (sync wait) | `QEventLoop` connected to `QNetworkReply::finished` |
| `job->error()` | `job->error() != QNetworkReply::NoError` |

Critical lifetime rule: QNetworkAccessManager must outlive its replies —
allocate with `new QNetworkAccessManager(this)` in the QObject-derived
classes (AsyncHTTPLookup / HTTPSubmit), never on the stack for async flows.

Qt signal/slot arity rule: connecting `QNetworkReply::finished` (0 args) to
a slot taking (QNetworkReply*) fails compilation with Qt's
static_assert "The slot requires more arguments than the signal provides" —
the slot must be argument-less and recover the reply from sender().

### 2. kcmcddb disabled (BUILD_KCM=OFF)

The KCM systemsettings module needs KF6::KIOCore/KIOWidgets, KF6::Solid,
KF6::WidgetsAddons, KF6::KCMUtils — none published to ohpcd. It is a
runtime configuration panel, not part of the audiocd link chain, so the
patch wraps `add_subdirectory(kcmcddb)` in `if(BUILD_KCM)` and the recipe
sets BUILD_KCM=OFF. Top-level find_package(KF6) reduced from
"Config I18n KIO WidgetsAddons KCMUtils" to "Config I18n CoreAddons".

### 3. Hidden KCoreAddons dependency made explicit

cdinfo.cpp `#include <KStringHandler>` (perlSplit) — KStringHandler lives
in KCoreAddons. Upstream never declares it (gets it transitively via KIO).
The patch adds `find_package(KF6 ... CoreAddons)` and links
`KF6::CoreAddons` PRIVATE (private because only cdinfo.cpp uses it; PUBLIC
would require every downstream consumer to find_package KF6CoreAddons).
Naming gotcha: FindKF6 component name is `CoreAddons` (resolves
KF6CoreAddonsConfig.cmake) but the imported target is `KF6::CoreAddons`.

### 4. Tests

Upstream registers **14** tests (tests/CMakeLists.txt `add_unit_tests()`,
count re-verified 2026-09-10 — the initial PR statement said 13, which
was an undercount; the list itself in the PR body already contained all
14 names). Per-test classification (rule4 逐项定性, re-verified with a
local network-enabled rerun on 2026-09-10):

| # | test | classification | CI result | technical reason |
|---|------|----------------|-----------|------------------|
| 1 | cdinfotest | offline | ✅ Passed (3/3) | pure CDInfo string/field round trips, no I/O |
| 2 | cachetest | offline | ✅ Passed (5/5) | local file cache under HOME (sandboxed) |
| 3 | asynchttplookuptest | network | not run in CI | live gnudb.org HTTP query; CI sandbox has no internet. Local rerun: transport OK (`Success`, 11 items) but FAIL at upstream data assertion — hardcoded revision 8 vs live revision 0 (upstream test snapshot from 2004, source comment itself says "If revision doesn't match, test probably needs to be updated") |
| 4 | asynccddblookuptest | network | not run in CI | live gnudb.org CDDBP (port 8880) query; same data-snapshot failure locally (hasRunTest FALSE — live DB no longer returns the 2006-era entry) |
| 5 | synchttplookuptest | network | not run in CI | same as #3: transport Success/11 items, data assertion revision 8≠live value (hasRunTest FALSE) |
| 6 | synccddblookuptest | network | not run in CI | same as #4: CDDBP transport works, entry 3e0c3a05 revision 17 assertion no longer matches live gnudb data |
| 7 | utf8test | network | not run in CI | live gnudb.org HTTP query for UTF-8 disc entry 13093f02; local rerun FAIL at hasRunTest (live DB returns different revision/data than the 3 hardcoded in the test) |
| 8 | sitestest | network | not run in CI | queries gnudb mirror list; **local rerun PASSED** (pure query, no data assertions). Excluded from CI solely because of the no-internet sandbox |
| 9 | asynchttpsubmittest | network+write | not run | POSTs a test entry (discid 3606ed05 "Bamse och Bronto") to the public gnudb submit.cgi — writing synthetic data into a public database is deliberately not executed even with network (side-effect policy); the submit transport path is covered by the 33-assertion loopback test in test_package |
| 10 | synchttpsubmittest | network+write | not run | same as #9 (sync variant, identical submit.cgi write side effect) |
| 11 | musicbrainztest | QSKIP | skipped (upstream behavior) | `#ifndef HAVE_MUSICBRAINZ5 → QSKIP` — libmusicbrainz5 not published to ohpcd, HAVE_MUSICBRAINZ5 undefined; upstream itself skips all 4 musicbrainz tests in this configuration (local rerun: "skipped") |
| 12 | asyncmusicbrainztest | QSKIP | skipped (upstream behavior) | same as #11 |
| 13 | musicbrainztest-severaldiscs | QSKIP | skipped (upstream behavior) | same as #11 |
| 14 | musicbrainztest-fulldate | QSKIP | skipped (upstream behavior) | same as #11 |

Executed in CI: 2/2 offline-runnable tests passed (`100% tests passed, 0
tests failed out of 2`). Local network-enabled evidence for the excluded
set: transport layer (KIO→QNetworkAccessManager rewrite) confirmed working
(lookup Success + 11 items; sitestest passes; 4 musicbrainz QSKIP matches
upstream no-libmusicbrainz behavior; 2 submit tests not executed by policy
— submit path covered by the loopback test). The residual lookup/utf8
failures are upstream data-snapshot rot (test comments themselves point to
the gnudb.org entries for updated data), not adaptation regressions.

### 5. Runtime environment quirks

- kconfig's libKF6ConfigGui.so has a relative DT_NEEDED
  `../../bin/libKF6ConfigCore.so` baked in at kconfig packaging time. Both
  the upstream ctest run and the test_package run need the symlink
  workaround at <exe-dir>/../../bin (kconfig 6.26.0
  _prepare_ctest_runtime_links precedent).
- ECM 6.26 KDEInstallDirs + conan layout puts libKCddb6.so in build bin/;
  ctest binary rpath resolves relative paths from there.

## Verification (conan create, ohos-aarch64 profile)

```
1/2 Test #1: cdinfotest ... Passed 0.23 sec
2/2 Test #2: cachetest ... Passed 0.08 sec
100% tests passed, 0 tests failed out of 2
libkcddb 26.04.3: Created package revision ...
libkcddb smoke test passed
```

test_package exercises: CDInfo set/get round trip, toString() xmcd
serialization, CDInfo::load() parse-back, Categories::cddbList/cddb2i18n,
Genres::cddbList/cddb2i18n — real API usage (R34), no external network.

Additionally (AI review verification-gap fix, round 2): a loopback HTTP
transport test drives the rewritten KIO → QNetworkAccessManager transport
end to end through the public KCDDB::Client API against a local
QTcpServer-based HTTP endpoint (127.0.0.1): lookup Success (CDDB 200)/
NoRecordFound (202)/ServerError (HTTP 500) paths, outgoing CGI query
verification (cmd=cddb query/hello/proto=6), and the submit path (HTTP
POST to /~cddb/submit.cgi with Category/Discid/User-Email/Submit-Mode/
Charset raw headers + text/plain Content-Type, CDDB 320 → Success). No
external network required.

Include-path fix (AI review P2): the installed headers live under
include/KCddb6/kcddb/ (lowercase .h files plus CamelCase forwarding
headers without extension). The test used <KCDDB/...> and <KCddb/...>
which only resolved by accident on the case-insensitive OHOS filesystem;
all includes were unified to the real installed paths (<kcddb/CDInfo>,
<kcddb/Client>, <kcddb/Config>, <kcddb/categories.h>, <kcddb/genres.h>).

SPDX fix (AI review P3): the 0001 patch accidentally dropped the
"SPDX-FileCopyrightText: 2002 Nadeem Hasan <nhasan@kde.org>" line from
submit.h while replacing the KIO forward declaration; restored so the
patch no longer touches the copyright block at all.

## Known packaging observation (not introduced by this PR)

The local W3 run reports L5a "libKCddb6.so missing DT_SONAME" and L5b
"absolute-path DT_NEEDED entries pointing at KF6 conan package paths".
Both stem from a repo-wide KDE packaging condition: none of the published
KF6 binaries (kconfig/ki18n/kcoreaddons in the ohpcd registry) carry a
DT_SONAME, so the linker embeds full paths when linking against them.
Upstream libkcddb sets SOVERSION 5 on the KCddb target, but the OHOS
cross-link of a SONAME-less dependency graph keeps the NEEDED entries as
paths. This matches the already-merged kconfig/ki18n packages (also
SONAME-less) and the CI L5 gate does not block on it (three consecutive
green CI runs: #42915/#42935/#42946). Fixing it requires an SONAME pass
across the whole KF6 baseline, which is out of scope for this PR.

## audiocd unblock note

With libkcddb/26.04.3 published, audiocd's KCddb dependency is satisfied.
audiocd's own KIO dependency is internal to the slave (it *is* a kioslave);
that adaptation is tracked separately in task #3888.
---

**编译结束**: 2026-09-09 18:09
**最终状态**: built
