# Upstream contribution material — libcsys

> **Status: PREPARED, NOT YET SUBMITTED.** Submitting requires a GitLab account
> (see §6). Everything needed to submit is in this file: a paste-ready issue body
> and the four fixes as unified diffs.

## 1. Why this is worth sending upstream

Four defects were found while adapting libcsys to HarmonyOS PC. All four are
**platform-independent** — none involves an OpenHarmony-specific code path:

| # | Defect | Still present upstream? |
|---|---|---|
| 1 | `InfoManager::update()` reads an empty CPU-frequency list out of range | **Yes — 5.0.1 identical** |
| 2 | `Power::~Power()` inverted loop condition → `takeFirst()` on an empty list | **Yes — 5.0.1 identical** |
| 3 | `SystemInfo::getHostname()` uses `gethostname()`'s 0 return as a string length | **Yes — 5.0.1 identical** |
| 4 | `NetworkInfo::getIOBytes()` three unconditional `removeFirst()` + unguarded `at(1)`/`at(9)` | **Yes — 5.0.1 identical** |

Verified against both released tarballs (official GitLab archives):

| Version | SHA-256 |
|---|---|
| v5.0.0 (`libcsys-v5.0.0.tar.gz`, 28945 B) | `8ba5ddcdcf6162a0db229f2b95312784a30760f09e919960fedb5fd9fe7f9cb9` |
| v5.0.1 (`libcsys-v5.0.1.tar.gz`, 28944 B) | `e94d996c0fa96de2b2254987894268184476ea2a201560e4ee0fed9e9c0c3c31` |

`csys/infomanager.cpp`, `csys/power.cpp`, `csys/systeminfo.cpp` and
`csys/networkinfo.cpp` are **byte-identical between v5.0.0 and v5.0.1**, so all
four defects are still live in the latest release.

Defects 1, 2 and 4 crash the process (SIGSEGV/SIGABRT); defect 3 silently
returns an empty hostname. Defects 1 and 2 trigger on **any** system where
`/proc/cpuinfo` has no `cpu MHz` field or where no systemd-logind/ConsoleKit
D-Bus provider exists — that includes containers and many non-desktop Linux
installations, not only OpenHarmony.

## 2. Minimal reproducers

```bash
git clone https://gitlab.com/cubocore/libcsys && cd libcsys
cmake -S . -B build && cmake --build build -j

# Defect 1 — crash as soon as /proc/cpuinfo has no "cpu MHz"
grep -c "cpu MHz" /proc/cpuinfo          # 0 on OpenHarmony / most containers
cat > /tmp/p1.cpp <<'EOF'
#include <csys/infomanager.h>
int main() { InfoManager m; m.update(); return 0; }
EOF
# link against the built libcsys + Qt6Core/Qt6DBus/Qt6Network, run → SIGSEGV

# Defect 2 — crash at exit whenever no logind/ConsoleKit provider is present
cat > /tmp/p2.cpp <<'EOF'
#include <csys/power.h>
int main() { Power p; return 0; }
EOF
# run → main returns normally, then SIGSEGV in ~Power()

# Defect 3 — hostname is always empty
cat > /tmp/p3.cpp <<'EOF'
#include <csys/systeminfo.h>
#include <QDebug>
int main() { SystemInfo s; qDebug() << s.getHostname(); return 0; }   // prints ""
EOF

# Defect 4 — crash when /proc/net/dev is unreadable or short
cat > /tmp/p4.cpp <<'EOF'
#include <csys/networkinfo.h>
int main() { NetworkInfo n; n.getIOBytes(); return 0; }
EOF
# run in a netns without interfaces, or with /proc/net/dev unreadable → SIGABRT
```

For defect 4 the abort messages observed on Qt 6.11.1 were:

```text
ASSERT: "!isEmpty()" in file .../QtCore/qlist.h, line 883          # empty /proc/net/dev
ASSERT failure in QList::at: "index out of range", ... qlist.h, line 513   # short row
```

A self-contained probe that compares the current and proposed parsing logic over
four crafted inputs (no access to the real `/proc/net/dev`) is included in this
archive: `reports/networkinfo-probe.cpp`, inputs
`reports/networkinfo-probe-case*.txt`, raw results
`reports/networkinfo-probe-evidence.txt`.

| Input | Current logic | Proposed logic |
|---|---|---|
| empty file | rc=134 `ASSERT: "!isEmpty()"` | rc=0 |
| headers only | rc=134 same | rc=0 |
| headers + one row + one short row | rc=134 `QList::at: "index out of range"` | rc=0 |
| real `/proc/net/dev` (13 interfaces) | rc=0 **but misses the first interface (`lo`)** | rc=0, all 13 interfaces counted |

The last row is worth noting on its own: the three blind `removeFirst()` calls
remove two header lines **and the first interface row**, so `lo` traffic is
never counted even in the happy path.

## 3. Proposed fixes (unified diffs)

Identical to the patches shipped in this archive
(`patches/0001-fix-runtime-crashes.patch`,
`patches/0002-fix-networkinfo-oob.patch`). Apply with `git apply -p1`.

```diff
--- a/csys/infomanager.cpp
+++ b/csys/infomanager.cpp
@@ -102,7 +102,7 @@
 	for ( int i = 0; i < nCPU; i++ )
 	{
 		mCpuPercents[i] << xPercents[i];
-		mCpuFrequencies[i] << xFrequencies[i];
+		mCpuFrequencies[i] << xFrequencies.value(i, 0.0);
 
 		while (mCpuPercents[i].count() > mDataPointsCount)
 		{
--- a/csys/power.cpp
+++ b/csys/power.cpp
@@ -113,7 +113,7 @@
 
 Power::~Power()
 {
-	while (providers.empty())
+	while (not providers.empty())
 	{
 		delete providers.takeFirst();
 	}
--- a/csys/systeminfo.cpp
+++ b/csys/systeminfo.cpp
@@ -89,10 +89,10 @@
 
 QString SystemInfo::getHostname() const
 {
-	char *hostname = new char[256];
-	int  size      = gethostname(hostname, 256);
+	char hostname[256] = { 0 };
+	gethostname(hostname, sizeof(hostname) - 1);
 
-	return QString::fromLatin1(hostname, size);
+	return QString::fromLatin1(hostname);
 }
 
 
--- a/csys/networkinfo.cpp
+++ b/csys/networkinfo.cpp
@@ -38,14 +38,25 @@
 
 	QStringList data = FileUtil::readListFromFile(netDataPath, QIODevice::ReadOnly);
 
-	// Remove the first three lines
-	data.removeFirst();
-	data.removeFirst();
-	data.removeFirst();
-
 	Q_FOREACH ( QString line, data )
 	{
-		QStringList bytes = line.trimmed().split(QRegularExpression("\\s+"));
+		QString row = line.trimmed();
+
+		// Skip the two header rows ("Inter-| Receive ..." / "face |bytes ...").
+		// The previous code called removeFirst() three times unconditionally,
+		// which is undefined behaviour whenever the file holds fewer rows: an
+		// unreadable or empty /proc/net/dev makes readListFromFile() return an
+		// empty list, and QStringList::removeFirst() on an empty list crashes.
+		if ( !row.contains( ':' ) )
+			continue;
+
+		QStringList bytes = row.split(QRegularExpression("\\s+"));
+
+		// Each interface row carries 16 counters; guard the indexes because
+		// QList::at() out of range is undefined behaviour (short rows crash).
+		if ( bytes.size() < 10 )
+			continue;
+
 		iobytes[0] += bytes.at(1).toULongLong();
 		iobytes[1] += bytes.at(9).toULongLong();
 	}
```

Notes on the fixes:

- Defect 1: `.value(i, 0.0)` keeps the "one entry per core" contract while making
  out-of-range reads return a default instead of reading past the end.
- Defect 2: one-character semantic fix; the loop body was already correct.
- Defect 3: removes the leak as a side effect (`new char[256]` was never freed).
  Using a zero-initialised stack buffer also guarantees termination for
  `QString::fromLatin1`.
- Defect 4: replaces "delete a fixed number of lines" with "skip non-interface
  lines", which both fixes the crash and stops discarding the first interface.
  Row shape is validated before indexing.

## 4. Verification performed here

- `conan create` of the patched recipe: exit code 0, both patches applied.
- Consumer test suite: **41/41 assertions pass** (`assertions=41 failures=0`,
  process exit code 0), covering `FileUtil`, `CpuInfo`, `MemoryInfo`,
  `SystemInfo`, `NetworkInfo`, `DiskInfo`, `InfoManager`, `BatteryManager`,
  `Power`, `StorageManager`.
- Probe evidence for defect 4 as tabulated in §2.
- Upstream has **no automated test suite** (`CMakeLists.txt` has no
  `enable_testing()`/`add_test()`, `meson.build` has no `test()`, no `tests/`
  directory), so no upstream test was modified or removed.

## 5. Paste-ready upstream issue body

```markdown
Title: Four runtime defects in csys (crash on systems without cpu MHz / logind, empty hostname, /proc/net/dev parsing)

Hello,

While packaging libcsys (v5.0.0, also present in v5.0.1) for a musl-based ARM64
system I hit four defects that are not platform specific. All four are still
present in v5.0.1 (csys/infomanager.cpp, csys/power.cpp, csys/systeminfo.cpp and
csys/networkinfo.cpp are byte-identical between v5.0.0 and v5.0.1).

1. InfoManager::update() reads an empty list out of range (csys/infomanager.cpp:105)

CpuInfo::updateInfo() only fills the frequency list when /proc/cpuinfo contains a
"cpu MHz" line. On systems without that field (containers, and the system I am
porting to) getCPUFrequencies() returns an empty list, and update() still indexes
it per core:

    mCpuFrequencies[i] << xFrequencies[i];      // crash

In a release build Q_ASSERT is compiled out, so this reads past the end and the
process segfaults as soon as update() is called. Suggested fix:

    mCpuFrequencies[i] << xFrequencies.value(i, 0.0);

2. Power::~Power() has an inverted loop condition (csys/power.cpp:116)

    Power::~Power()
    {
        while (providers.empty())        // should be !providers.empty()
        {
            delete providers.takeFirst();
        }
    }

When no systemd-logind/ConsoleKit D-Bus provider is present, providers is empty,
the condition is true, and takeFirst() is called on an empty list. The program
appears to run fine and then crashes while unwinding at exit.

3. SystemInfo::getHostname() always returns an empty string (csys/systeminfo.cpp)

    char *hostname = new char[256];
    int  size      = gethostname(hostname, 256);
    return QString::fromLatin1(hostname, size);

gethostname() returns 0 on success, not the length, so the string is always
empty; the buffer is also never initialised and never freed. A zero-initialised
stack buffer makes the length argument unnecessary.

4. NetworkInfo::getIOBytes() aborts on unreadable or short /proc/net/dev (csys/networkinfo.cpp)

    data.removeFirst();      // three times, unconditionally
    ...
    iobytes[0] += bytes.at(1).toULongLong();
    iobytes[1] += bytes.at(9).toULongLong();

If /proc/net/dev cannot be read, readListFromFile() returns an empty list and
removeFirst() aborts ("ASSERT: !isEmpty()"). A file with fewer than three rows
(network namespace without interfaces) aborts the same way, and rows with fewer
than ten fields abort on at() ("QList::at: index out of range"). The three blind
removeFirst() calls also delete the first interface row, so the loopback
counters are never included even on a normal system.

We fixed all four locally and they make the library usable on our system; the
diffs are below. Would you be interested in a merge request?

    [paste the §3 diff here]

Tests: the project has no automated test suite, so we validated with a consumer
test exercising FileUtil, CpuInfo, MemoryInfo, SystemInfo, NetworkInfo, DiskInfo,
InfoManager, BatteryManager, Power and StorageManager (41 assertions, all
passing), plus a probe that compares the old and new /proc/net/dev parsing over
crafted inputs (empty file, headers only, short row, real file).

Thanks for the library.
```

## 6. How to submit

- Upstream code: <https://gitlab.com/cubocore/libcsys>
- Issue tracker (per the project README): <https://gitlab.com/groups/cubocore/coreapps/-/issues>
- Suggested route: open the issue above, then offer a merge request against
  `master` with the §3 diff (one commit, or two commits splitting defect 4 from
  1–3 as done in this archive).
- **Not done from here**: submission needs a GitLab account and an explicit
  decision to post publicly under the applicant's name, so it is left to the
  applicant. Nothing in this repository depends on the outcome.
