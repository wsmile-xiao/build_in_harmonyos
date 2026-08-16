# acf-openssh 0.11.2 W0 dependency report

## Current result

W0 passed on 2026-08-15. The compatible Lua 5.4 dependency was split into
issue #2117 and PR #5204 as required. PR #5204 is merged at commit
`1e58af5de4c938790b33de891fe9521e2163d249`, and the official anonymous
`ohpcd` Conan v2 endpoint now returns `luaposix/36.3.1.1` recipe revision
`8bf168040d86e8aabd8feca6afc33a5d`, published at
`2026-08-15T10:08:35Z`. The acf-openssh branch still contains no luaposix
files.

## Original conflict

The published dependency contracts were:

```text
acf-core/0.24.1          -> lua/5.4.8
acf-lib-lua5.4/0.11.1   -> lua/5.4.8
lua-subprocess/0.02      -> lua/5.4.8
luaposix/36.3            -> lua/5.5.0
```

Resolving them in one graph failed before binary selection:

```text
ERROR: Version conflict: Conflict between lua/5.5.0 and lua/5.4.8 in the graph.
Conflict originates from luaposix/36.3
```

This dependency is not optional. `openssh-model.lua` directly executes
`require("posix")`; `acf.fs` and acf-core model helpers also use the same
runtime chain. A test-only shim would violate the deployed application.

## Separate dependency action

Issue #2117 and PR #5204 introduced `luaposix/36.3.1.1` for the Lua 5.4 ABI.
The version was incremented because the remote already contained a different
`luaposix/36.3.1` recipe revision. The acf-openssh branch contains no
luaposix files.

## Candidate integration result

An isolated OHOS shadow run overlaid PR #5204 only in the temporary source
snapshot. It built `luaposix/36.3.1.1` from source, then built and tested only
`archives/a/acf-openssh/0.11.2`. The final run passed with `setup_rc=0`,
`build_rc=0`, L0/L1/L4 pass, and all 48 package checks passing:

```text
acf commit: b4c79d1128721ac86656048d1d8d7ce052b0769f
run: /storage/Users/currentUser/ohpc-ci-shadow/runs/b4c79d112872-20260813T072224Z-run-25623
build log sha256: 247ed439056b1946e1ebd8b4595f44bd4923920e677632f4a7df7f414485a32c
```

This proves candidate graph and runtime compatibility, but it does not close
R36: a release job still requires the dependency to exist in the official
registry without local export or `--build=missing` fallback.

## Published dependency evidence

The release condition above is now cleared. The repository-configured remote
is `https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`; its
anonymous Conan v2 recipe-revisions endpoint returned HTTP 200 with:

```json
{
  "reference": "luaposix/36.3.1.1",
  "revisions": [{
    "revision": "8bf168040d86e8aabd8feca6afc33a5d",
    "time": "2026-08-15T10:08:35Z"
  }]
}
```

## Final dependency evidence

The next formal or device run should confirm the complete graph without an
overlay:

```sh
conan download "luaposix/36.3.1.1" -r=ohpcd --only-recipe
conan graph info \
  --requires="acf-core/0.24.1" \
  --requires="acf-lib-lua5.4/0.11.1" \
  --requires="lua-subprocess/0.02" \
  --requires="luaposix/36.3.1.1" \
  --requires="openssh/10.0p1" \
  -r=ohpcd --build=never
```

Success requires a single Lua version (`lua/5.4.8`) and no local dependency
fallback.
