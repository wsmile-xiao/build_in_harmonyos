# DRAFT — Compile-fail (expect-to-fail) upstream test suites on OHOS

> Status: DRAFT (contributor 9C4A) | Source: trompeloeil/49 adaptation, task #11301, PR #10341
> Environment: HarmonyOS PC aarch64, OHOS SDK clang 15.0.4 / libc++ 15, Conan 2.29.1 (OHOS), toybox user space

## 1. The problem class

Some upstream projects encode compile-time contracts as **expect-to-fail test
cases**: one translation unit per contract, each required to *fail to compile*
with a diagnostic that must match a declared oracle. The oracle is text, not an
exit code. trompeloeil's negative suite is the verified instance used here:

```cpp
// return_wrong_type_first.cpp (upstream, unmodified)
// exception: c++11                                  <- skip rule for the compiler/standard
// pass: RETURN value is not convertible to the return type of the function
```

and it is driven by a fan-out script that assumes a GNU user space:

```sh
# check_errors.sh (upstream, unmodified)
cd compilation_errors
files=`ls *.cpp`
parallel ../verify_compilation_error.sh ::: $files | tee $failfile
FAILURES=`cat $failfile | grep FAIL | wc -l`        # signal = FAIL lines, not exit codes
exit $FAILURES
```

On OHOS two independent prerequisites are missing or wrong:

1. **Execution layer** — GNU `parallel` does not exist in the toybox user
   space, and `mktemp` (used per case) defaults to `/tmp`, which is read-only
   (E002). The suite cannot start.
2. **Oracle layer** — whether the OHOS compiler emits the diagnostics the
   upstream `// pass:` regexes declare is an empirical property of
   clang 15 + libc++ 15 on OHOS. It must be measured per case; assuming it
   (or rewriting the oracle) is not acceptable.

If the suite is simply skipped, the package loses its strongest assertion
class while still reporting "upstream tests pass". That is the false green this
entry is about.

## 2. Why existing knowledge is not enough

| Existing entry | What it covers | What it does not |
|---|---|---|
| E002 | `/tmp` read-only → use `$TMPDIR` | does not define a fan-out driver, nor the oracle accounting |
| E063 | `-Werror` warning categories on musl/clang | about warnings-as-errors in the build, not compile-fail assertions |
| E325 | resolving an available shell before running test_package scripts | about *which shell*, not *what the suite needs inside it* |
| E418 | runtime negative oracle on Windows PowerShell (empty-string binding) | runtime harness, not compile-time assertions |
| E423 | destructive runtime negative for cross binutils package ownership | removes package payload; here the compiler is the oracle |
| eigenvalue/negative-include draft | consumer include-path boundary proof | consumer-side provenance, not upstream expect-to-fail suites |

No existing entry defines the execution model for compile-fail suites on OHOS,
the per-case PASS/FAIL/excluded accounting, or the rule that diagnostic drift
must be reported rather than silenced.

## 3. Verified resolution (trompeloeil/49)

The recipe keeps the cases, the per-case verify script and every oracle
**untouched**, and replaces only the fan-out/environment layer inside `build()`:

```python
driver = os.path.join(neg_dir, os.pardir, "verify_compilation_error.sh")
tmpdir = os.path.join(self.build_folder, "negative-tests-tmp")   # /tmp is read-only
os.makedirs(tmpdir, exist_ok=True)

def run_case(case):
    env = dict(os.environ)
    env["CXX"] = cxx                       # from tools.build:compiler_executables (R33)
    env["CXXFLAGS"] = "-std=c++" + std
    env["TMPDIR"] = tmpdir
    proc = subprocess.run([sh, driver, case], cwd=neg_dir, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return case, proc.stdout or ""

with ThreadPoolExecutor(max_workers=2) as pool:
    results = dict(pool.map(run_case, sorted(cases)))

# PASS   = failed to compile AND diagnostic matched the declared regex
# FAIL   = compiled successfully OR diagnostic mismatch -> conan create fails
# neither = excluded by the case's own // exception: rule (upstream behavior)
```

The suite runs at **C++14 and C++20** (C++20 activates coroutine-guarded
cases), and the counts are reported per standard.

## 4. Evidence (real runs, 2026-09-16)

Manual probe on the untouched tree (`xargs -P2`; the recipe uses the thread
pool for portability):

```text
TOTAL=68 PASS=50 FAIL=0     # C++14: 18 cases excluded by upstream // exception: rules
TOTAL=68 PASS=68 FAIL=0     # C++20: coroutine cases all execute
```

Inside `conan create` (clean source cache, recipe-driven):

```text
trompeloeil/49: [negative-compile c++14] cases=68 executed=50 pass=50 fail=0 excluded=18
trompeloeil/49: [negative-compile c++20] cases=68 executed=68 pass=68 fail=0 excluded=0
```

Result: OHOS clang 15 + libc++ 15 diagnostics matched **every** upstream oracle
— zero drift, zero exclusions beyond the upstream rules, zero `// pass:`
rewrites. Neighbouring runtime suites also passed unmodified (C++14: 1361
assertions / 604 cases; C++20 incl. coroutines: 1394 / 615).

## 5. Cross-library applicability

Applies to any upstream suite whose assertion is compile failure + diagnostic
text, when compiled as part of the Conan build:

- mocking frameworks with negative suites (trompeloeil `compilation_errors/`);
- API-boundary negative tests of frameworks/libraries (Catch2-style
  `CompileTime` checks; cmocka/doctest negative cases);
- codegen/DSL negative fixtures and compile-time trait/static-assert contracts.

Applicability condition: the suite must expose a per-case equivalence class
(single translation unit + declared expected diagnostic) and a signal that is
text-matching rather than exit-code-only.

## 6. Boundaries and governance

- This entry does **not** claim all compile-fail suites are portable; it gives
  the measurement procedure and the two OHOS prerequisites (fan-out driver,
  writable `TMPDIR`).
- Diagnostic drift, if ever observed, is reported with the raw compiler output
  and handled through a declared mechanism (case-comment update upstream, or a
  documented exclusion) — **never** by editing `// pass:` regexes or filtering
  `FAIL` lines.
- The upstream driver is not replaced by "no driver": skipping the suite and
  reporting success is the forbidden path.
- `TMPDIR` must live inside the build folder; `/tmp` is never a fallback.

## 7. Draft review and de-duplication

`draft-review` on this draft: signature/root_cause/rec all present; the closest
formal entries are listed in `similar_to` (E002/E063/E325/E418/E423). The
E325 similarity (gray zone) is structural only: E325 resolves *which shell*
runs a test_package script; this entry supplies what a compile-fail suite needs
*inside* the driver and how its oracle is accounted. E418/E423 are runtime
negatives; the gtest/catch2/cmocka/doctest drafts cover framework wiring
(CMake components, API migration, CTest injection, submodule handoff), not the
compile-fail assertion model.

## 8. Note

The companion finding of this adaptation — upstream CMake `file(DOWNLOAD)`
fallbacks that silently swap the framework major version at configure time — is
deliberately **not** submitted as a new entry: the class is already covered by
E342 and `DRAFT-cmake-test-framework-fetch-to-conan-find-package` (FetchContent
variant). The trompeloeil evidence for it stays in the archive `notes.md` as an
adaptation note.
