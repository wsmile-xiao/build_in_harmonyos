# W0 dependency report: jflex/1.9.1

Date: 2026-08-17
Issue: 2241

## Conan dependency graph

- Required packages: none
- Optional packages: none
- Result: PASS; no dependent library issue/PR is needed.

## Build and runtime prerequisites

- JDK 11 or newer is required; the recipe installs the project-proven BishengJDK 17.0.13 in the isolated HOME when Java is absent.
- Maven is a build tool, not a packaged runtime dependency. The recipe finds an installed Maven or downloads the official Apache Maven 3.6.3 archive with SHA256 verification.
- Maven resolves the upstream POM dependencies from Maven Central. They are not Conan packages and are not adapted in this PR.

## Source integrity

- Official release URL: `https://github.com/jflex-de/jflex/releases/download/v1.9.1/jflex-1.9.1.tar.gz`
- SHA256: `e0c1e9eef91ff6df04d73fa5eaff13f3a02b679fee1474e5ccae007224df6df6`
- Upstream SHA1: `a0f90647a2d7e48ac0fb7bb2e787a12b0b4af19a`
- Local SHA1 verification: matched

## Real-device shadow CI

Run `codex-jflex-jflex-1.9.1-2241-b-shadow-r4-20260817-132158-24356` used Conan 2.29.1, the OHOS armv8 profile, an isolated HOME/CONAN_HOME/TMPDIR, and the global runner try-lock.

- Exit code: 0; build summary: 1/1 successful.
- Registry collision gate: passed; `jflex/1.9.1` was not already published.
- Conan dependencies: none; no dependent library issue or PR is needed.
- Upstream Maven/Surefire: 133 executed, 132 passed, 0 failed, 1 skipped.
- Consumer test: 19/19 checks passed through a real `tool_requires` build context and its `conanbuild` environment.
- Consumer coverage: buildenv paths, wrapper version, two lexer generations, two javac compilations, basic semantics, Unicode identifiers/text, and lexical-state transitions.
- Package artifacts: `libexec/jflex-full-1.9.1.jar`, `libexec/jflex.sh`, and `licenses/LICENSE_JFLEX`.
- Gates: L0 pass, L1 pass, L2 skip (no native `bin/`), L4 pass, L5 warn (JVM artifact is under `libexec/`).
- The final r4 used a fresh Conan home and reused only the 78 MB jflex-specific Maven repository populated by the cold r3 run.

The shadow CI pipeline completed successfully; the L2 skip and L5 warning are expected for this JVM build tool and are non-blocking.
