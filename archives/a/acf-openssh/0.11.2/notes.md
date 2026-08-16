# acf-openssh 0.11.2 adaptation notes

## Current status

Issue #2112 has a complete Conan recipe, one focused portability patch, and a
functional consumer test. Candidate integration passed on an OHOS device.

The original blocker was the lack of a Lua 5.4-compatible luaposix package.
Issue #2117 and PR #5204 provide `luaposix/36.3.1.1`; its final commit passed
shadow CI and formal CI. PR #5204 is now merged at
`1e58af5de4c938790b33de891fe9521e2163d249`. The official anonymous `ohpcd`
Conan v2 endpoint returns recipe revision
`8bf168040d86e8aabd8feca6afc33a5d`, published at
`2026-08-15T10:08:35Z`; W0 is closed. Formal acf-openssh CI still needs to
exercise the released dependency graph.

Formal CI builds #24119 and #24130 did not reach repository checkout or any
Conan command. On two different workers, the SSH bridge returned connection
refused for the first worker preparation command and then for `git --version`.
The bot classified both runs as source download timeouts, but no source URL
was requested. These are worker infrastructure failures and are recorded in
`reports/local-validation.md`; changing the verified upstream source URL or
recipe cannot correct them.

Formal CI #24148 reached `conan-build-test` and exposed a separate repository
gate: contributor drafts are allowed only in `knowledge/drafts/`. The E327
acf-openssh draft pair is stored there. The repository
knowledge quality script now passes KC1-KC5 with zero errors.

## Upstream source

- Project: Alpine Configuration Framework OpenSSH module
- Upstream: `https://gitlab.alpinelinux.org/acf/acf-openssh`
- Version: `v0.11.2`
- Official archive:
  `https://distfiles.alpinelinux.org/distfiles/v3.18/acf-openssh-v0.11.2.tar.gz`
- SHA-256: `668be900964b2e42e55c3f921e2d2a1d54ca618583a6681ccaefc01fbf2aa793`

## Source and build analysis

The release contains no C/C++ source. It ships two Lua modules, eight LSP
templates, one menu file, and one roles file. The top-level Makefile has an
empty `all` target and installs `openssh*` with `cp -a` into
`/usr/share/acf/app/openssh` under `DESTDIR`.

Three upstream LSP entries are relative symlinks to ACF shared templates:

- `openssh-expert-html.lsp -> ../expert-html.lsp`
- `openssh-logfile-html.lsp -> ../logfile-html.lsp`
- `openssh-status-html.lsp -> ../status-html.lsp`

The target HMDFS storage omits those links during extraction/copy and rejects
explicit `symlink(2)` with `PermissionError: [Errno 13]`. Following the
project's no-link guidance, `package()` materializes the corresponding real
templates from the declared `acf-core/0.24.1` dependency as regular files.
The consumer test byte-compares all three files with their dependency sources.

The package keeps the upstream `/usr` application resource layout. It has no
ELF artifact and does not declare a commands manifest.

Upstream provides no test directory and no `check` or `test` Makefile target.
The consumer test therefore reports only adaptation checks and does not claim
an upstream test pass rate.

## Runtime dependencies

`openssh-model.lua` directly loads `modelfunctions`, `posix`,
`acf.validator`, `acf.fs`, and `acf.format`. The runtime graph contains:

- `acf-core/0.24.1`
- `acf-lib-lua5.4/0.11.1`
- `lua-subprocess/0.02`
- `luaposix/36.3.1.1`
- `lua/5.4.8`
- `openssh/10.0p1`

These requirements belong to the production recipe. None is hidden inside
`test_package`, and no dependency adaptation is included in this branch.

## Portability patch

Upstream hard-codes `/etc/ssh/sshd_config`, while the packaged OpenSSH config
is under `usr/local/etc`. The patch reads `ACF_OPENSSH_CONFIG` with the
upstream path as fallback. `package_info()` sets that variable to the
`openssh/10.0p1` package config for normal Conan consumers. The functional
test overrides it with an isolated temporary file and never writes `/etc`.

## Consumer test

The test compiles a Lua 5.4 runner against the published `lua/5.4.8` static
library. It verifies all 12 application resources and byte-compares the three
materialized shared views, then loads the packaged controller and model with
real Conan dependencies. It exercises controller action exports, config
parsing, invalid address/port rejection, a successful config update, boolean
serialization, and syslog facility parsing. There are 48 checks in total:
16 layout checks plus 32 Lua functional checks.

OpenRC start/stop and live `ps`/`netstat` peer discovery remain integration
limitations: HarmonyOS does not provide Alpine's `/etc/init.d/sshd` and
`rc-update` service model. Those paths are not faked as passing tests.

## Candidate shadow evidence

The isolated candidate run used the exact `acf-openssh` commit below and
overlaid only the already-reviewed `luaposix` PR commit in the temporary
input. No luaposix files are present in this branch.

```text
run: /storage/Users/currentUser/ohpc-ci-shadow/runs/b4c79d112872-20260813T072224Z-run-25623
acf commit: b4c79d1128721ac86656048d1d8d7ce052b0769f
dependency commit: 754dc4142f7ef00331cd0614c1cfe7cc9e104c81
setup_rc: 0
build_rc: 0
L0: pass
L1: pass
L2: skip (no bin directory)
L4: pass
L5: warn (pure resource package has no bin/lib)
build log sha256: 247c6332177d14f0ef863ec952a227e2a89040f04c4f808f49c534d343783256
```

## Resume commands

Run against the published dependency without the temporary source overlay:

```sh
conan download "luaposix/36.3.1.1" -r=ohpcd --only-recipe
CI_PACKAGES="archives/a/acf-openssh/0.11.2" zsh ci/conan/build_and_test.sh
```

Expected scope is one package. L0 and L1 must pass. L2 skips because this
package intentionally has no `bin/`; L5 may warn for the same pure-resource
layout.
