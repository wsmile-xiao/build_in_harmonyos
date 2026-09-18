# OHOS conan aggregated env only propagates whitelisted variables

> **Contributor**: codex | **Status**: DRAFT | **Created**: 2026-09-13

## Symptom

A recipe sets `env.define("TMPDIR", ...)`, `env.define("PWD", ...)` or
`env.define("PKG_CONFIG", ...)` in `_build_environment()`, yet the build
step behaves as if the variable were unset:

- `config.status[1510]: can't create .../subs1.awk: Permission denied`
  (the temp dir fell back to the cwd)
- `configure: error: working directory cannot be determined`
  (mksh validates `$PWD` and falls back to a getcwd that returns EBADF
  on the distributed fs)

while the same variables exported in the job env.sh reach every child
without issue.

## Root cause

The OHOS-adapted conan writes its aggregated env file
(`conanbuildenv-*.sh`) for a whitelist of variables only: `PATH`,
`PKG_CONFIG_PATH`, `CONFIG_SHELL`, `SHELL`, `LD_LIBRARY_PATH`,
`AUTOTOOLS_DEV_*`. Anything else set via `env.define` in the recipe is
dropped from the aggregated file. Variables inherited from the parent
conan process still propagate through normal process inheritance, which
is why the job env.sh channel works and the recipe env.define channel
does not.

## Decision rule

1. Source the aggregated `conanbuild.sh` in a shell and echo each
   expected variable. Empty brackets = the whitelist dropped it.
2. Move the variable into the job-level env.sh (exported before conan
   create) — every child, including libtool scripts and config.status,
   then sees it through normal inheritance.
3. For values that must be computed per build (paths under the build
   folder), write them into the consuming build script itself (sed the
   generated configure/config.status in the recipe) rather than relying
   on env propagation.

## gtk2 2.24.33 evidence

Three variables lost through this channel in one device session:

| Variable | Missing effect | Fix channel |
|---|---|---|
| TMPDIR | clang temp files landed on the read-only /tmp | job env.sh |
| PWD | mksh getcwd validation failed ("working directory cannot be determined") | recipe-internal: env.define("PWD", source_folder) works because os.environ mutation reaches children directly, but only for direct children — verify per case |
| PKG_CONFIG | config.status probes degraded | job env.sh |

## Boundary

This draft covers the propagation channel only. The underlying fs
behaviors that make these variables matter (0700 mktemp dirs, read-only
/tmp, getcwd EBADF) are covered by their own drafts.
