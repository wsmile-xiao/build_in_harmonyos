# luarocks5.5 3.13.0 Path B upstream-test report

## Basic information

- Library: `luarocks5.5`
- Upstream version: `3.13.0`
- Task branch: `feat/luarocks5.5-3.13.0`
- Task type: normal OpenHarmony PC points-competition task
- Source archive: `https://luarocks.org/releases/luarocks-3.13.0.tar.gz`
- Source SHA-256: `245bf6ec560c042cb8948e3d661189292587c5949104677f1eecddc54dbe7e37`
- Conan dependency used by this adaptation: `lua/5.5.0`

## Upstream test inventory

The exact `luarocks-3.13.0.tar.gz` release archive contains the following upstream test assets:

- `smoke_test.sh`
- `test_regression.sh`
- `.busted`
- `spec/README.md`
- 44 upstream `*_spec.lua` files under `spec/`

The upstream rockspec defines the Busted-based test command and declares test dependencies including `luacov` and `busted-htest`. On Unix, upstream excludes the `ssh` and `git` tagged tests.

## Original upstream-test result in the Lua 5.5 environment

The reproduced upstream Busted run with Lua 5.5 reached the Busted runner but did not satisfy Path A:

- Test files executed by Busted: 43
- Busted cases executed: 55
- Passed: 52
- Skipped: 3
- Errors: 178
- Result: not Path A

Evidence log:

- `F:\jifensai\.tmp-ohpcd-scripts\run-luarocks-upstream-20260802.out.log`

Representative upstream failure:

```text
Error: Could not satisfy dependency lua >= 5.1, < 5.5
Missing dependencies for luacov 0.15.0-1:
   lua >= 5.1, < 5.5 (not installed)
```

## Root cause

The task target is explicitly `luarocks5.5`, and the submitted recipe configures LuaRocks with the repository `lua/5.5.0` dependency. The upstream test environment, however, attempts to install `luacov 0.15.0-1` as a test dependency. That test dependency declares `lua >= 5.1, < 5.5`, so it is incompatible with the Lua 5.5 VM used for this task.

The upstream release rockspec also contains duplicate `tag` fields, so `luarocks test` is not a reliable single-command Path A runner without first adapting the upstream test metadata.

These are upstream test-suite/environment constraints, not evidence that the submitted package commands fail to run.

## Why Path B is required

Path A requires all upstream tests to execute and pass with no failures, skips, or unhandled exclusions. The reproduced upstream result contains skipped cases and dependency-resolution errors under Lua 5.5. Therefore this task is submitted as Path B instead of claiming a full Path A pass.

## Minimal adaptation plan

The package adaptation does not patch upstream functional code. It packages LuaRocks 3.13.0 for Lua 5.5 and records the upstream-test limitation separately.

For upstream test acceptance, the minimal Path B treatment is:

1. Keep the complete upstream inventory visible in `MANIFEST.yml`, `manifest.yaml`, `notes.md`, and this report.
2. Do not count the self-written Conan `test_package` as upstream tests.
3. Explain the Lua 5.5 versus `luacov < 5.5` test-dependency incompatibility.
4. Use deterministic consumer validation to prove the packaged LuaRocks commands are usable with Lua 5.5.
5. Ask reviewers to evaluate the upstream-test exception through the Path B Issue/PR flow.

## Added consumer validation

The Conan `test_package` exercises the installed package, not merely file presence:

- `luarocks --version` reports LuaRocks `3.13.0`
- `luarocks config lua_version` reports Lua `5.5`
- `luarocks-admin --version` runs successfully
- `luarocks help install` runs successfully
- an invalid LuaRocks command returns non-zero
- `luarocks lint` rejects an intentionally invalid rockspec

This adds positive smoke coverage plus fault-injection coverage while keeping upstream-test accounting separate.

## Local validation already produced

- Linux Conan `Release`: passed
- Linux Conan `Debug`: passed
- `test_package`: passed in both build types
- Fault injection: invalid command and invalid rockspec lint both returned deterministic failures

Evidence log:

- `F:\jifensai\.tmp-ohpcd-scripts\run-luarocks-conan-20260802.err.log`

## Non-weakening statement

No upstream test is hidden or reclassified as passed. The package recipe does not weaken the upstream source code or test behavior. The Path B report exists because the upstream test harness currently requires a test dependency whose published Lua version range excludes Lua 5.5, while the actual submitted package is required to target `lua/5.5.0`.
