# uwsgi-logzmq 2.0.31 adaptation notes

## Issue

- No explicit issue number was found in the repository metadata or the local
  adaptation-summary documents searched for `uwsgi-logzmq` / `logzmq`.
- Handoff marker: issue pending.

## Source

- Upstream: https://github.com/unbit/uwsgi
- Stable tag: 2.0.31
- Source archive: https://github.com/unbit/uwsgi/archive/refs/tags/2.0.31.tar.gz
- SHA256: d5fb7b058a6e037cad1f0fb8841de56d673d80a3af036bba830143b60c67c3dc
- Local source analysis also checked the PyPI sdist
  `uwsgi-2.0.31.tar.gz`, SHA256
  `e8f8b350ccc106ff93a65247b9136f529c14bf96b936ac5b264c6ff9d0c76257`.
  The historical `https://projects.unbit.it/downloads/uwsgi-2.0.31.tar.gz`
  endpoint failed on Windows curl due to an expired certificate, so the recipe
  follows the existing `uwsgi-router_http/2.0.31` GitHub tag source.

## W0 dependency check

- Required dependency: `zeromq/4.3.5`.
- `conan download zeromq/4.3.5 -r=ohpcd --only-recipe` completed locally.
- `conan list "zeromq/4.3.5:*" -r=ohpcd` showed an OHOS armv8 Release clang 15
  shared package revision in `ohpcd`.
- No dependency adaptation was mixed into this PR.

## Build

- Builds the upstream `plugins/logzmq` dynamic plugin with uWSGI's
  `uwsgiconfig.py --plugin` entry point.
- The recipe writes a local `buildconf/logzmq_conan.ini` profile under the
  extracted source tree.
- The profile inherits `minimal`, disables unrelated optional features, enables
  `plugins = logzmq`, and injects ZeroMQ include paths from the Conan
  dependency into profile `cflags`. The ZeroMQ library path is passed through
  the build environment `LDFLAGS`, which `uwsgiconfig.py` reads directly.
- The recipe validates the configured C compiler path before passing it to
  `uwsgiconfig.py`. On the current OHOS worker the profile still points at the
  old `/data/service/hnp/bin/clang`, while the usable compiler is
  `/storage/Users/currentUser/usr/local/bin/clang`.
- `plugins/logzmq/uwsgiplugin.py` contributes `LIBS = ['-lzmq']`.
- No source patches are applied.
- The plugin installs as `lib/uwsgi/logzmq_plugin.so`.

## Upstream tests

- uWSGI provides global `make check`, `make tests`, and `make unittests`
  targets.
- There is no standalone registered upstream test for the `logzmq` plugin in
  the 2.0.31 source tree.
- The official inventory for this package is therefore recorded as 0/0 for
  upstream plugin-specific tests.

## Added test_package

- Builds one C consumer probe.
- The probe is compiled directly with the resolved C compiler instead of using
  CMakeToolchain, because the current worker profile still contains an obsolete
  `/data/service/hnp/bin/clang` path that CMake treats as fatal.
- The probe validates the packaged plugin is a non-empty ELF shared object and
  contains expected uWSGI/ZeroMQ strings or dynamic-symbol names:
  `logzmq_plugin`, `logzmq`, `zeromq`, `log-zeromq`, `zmq_connect`, and either
  `zmq_sendmsg` or the ZeroMQ 4 `zmq_msg_send` symbol.
- The probe intentionally does not require independent `dlopen(..., RTLD_NOW)`
  success because uWSGI plugins are normally loaded by the uWSGI process, whose
  global symbols satisfy plugin references.

## Local validation

- Worktree: `D:\harmonyos\worktrees\uwsgi-logzmq`
- Branch: `feat/uwsgi-logzmq-2.0.31`
- Main Apache Arrow worktree was not modified or branch-switched.
- Completed local checks:
  - `python -m py_compile archives/u/uwsgi-logzmq/2.0.31/conanfile.py archives/u/uwsgi-logzmq/2.0.31/test_package/conanfile.py`
  - `conan inspect archives/u/uwsgi-logzmq/2.0.31`
  - `conan export archives/u/uwsgi-logzmq/2.0.31 --user=ohpcd --channel=stable`
  - `conan graph info archives/u/uwsgi-logzmq/2.0.31 -r=ohpcd --build=never`
  - `conan create archives/u/uwsgi-logzmq/2.0.31 --user=ohpcd --channel=stable -r=ohpcd --build=never`
  - `git diff --check -- archives/u/uwsgi-logzmq`
- OHOS runner notes:
  - r1/r2 reached only early setup and failed because the new isolated
    `CONAN_HOME` did not yet have the OHOS settings/profile. The job was fixed
    by copying the worker's known-good `settings.yml` and importing
    `ci/conan/profiles/ohos-aarch64`.
  - r3 reached package build, downloaded `zeromq/4.3.5` from `ohpcd`, and
    downloaded uWSGI 2.0.31 through the mirror fallback. Build then failed in
    `uwsgiconfig.py` compiler probing because the profile compiler path
    `/data/service/hnp/bin/clang` was absent on this worker.
  - r4 built and packaged `logzmq_plugin.so`, then failed in test_package
    CMake configure for the same obsolete profile compiler path. The
    test_package was changed to invoke the resolved C compiler directly.
  - r5 passed end-to-end:
    - Runner:
      `/storage/Users/currentUser/ohos-test-runs/codex-uwsgi-logzmq-uwsgi-logzmq-2.0.31-20260814-032105-conan-r5-20260814-033303-64173`
    - Package reference:
      `uwsgi-logzmq/2.0.31#b7878005966c331d679cdcf020dad3e5:3ef885ef6b05220b66fa03c1f22cac18a98a0134#71676c942fde659bb792b6af1e2d3e3b`
    - Packaged plugin: `lib/uwsgi/logzmq_plugin.so`, 174528 bytes.
    - `test_package` output:
      `uwsgi-logzmq plugin probe OK: 174528 bytes`.
    - CI summary: `Total: 1`, `Success: 1`, `Failed: 0`.
    - Gate summary: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=skip`
      (no `bin/`), `L4_RESULT=pass`, `L5_RESULT=pass`.
- Local graph note: this Windows host only has the default Windows/MSVC Conan
  profile, so `conan graph info` / `conan create --build=never` resolve the
  recipe and dependency edge but report the Windows `zeromq/4.3.5` and
  `uwsgi-logzmq/2.0.31` binaries missing. This is expected and does not
  contradict the W0 OHOS package check above.
- Source URL note: a direct Windows curl request to the GitHub tag tarball timed
  out during this session. The URL and SHA256 are inherited from the existing
  `uwsgi-router_http/2.0.31` recipe that targets the same upstream tag.

## Next validation commands

Run only when a single-package OHOS/shadow CI slot is available:

```sh
CI_PACKAGES="archives/u/uwsgi-logzmq/2.0.31" zsh ci/conan/build_and_test.sh
```

If using the shadow CI wrapper:

```sh
/path/to/run-ohos-shadow-ci.sh archives/u/uwsgi-logzmq/2.0.31
```
