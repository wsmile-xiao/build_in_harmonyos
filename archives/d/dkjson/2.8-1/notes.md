# dkjson 2.8-1 adaptation notes

## Scope

This package adds David Kolf's dkjson 2.8-1 as a pure Lua dependency for the
Busted/Vusted chain used by nvim-lspconfig Path B validation.

## Source

- Upstream homepage: https://dkolf.de/dkjson-lua/
- LuaRocks release: 2.8-1
- Source archive: https://dkolf.de/dkjson-lua/dkjson-2.8.tar.gz
- SHA256: 24e8cd3beb91c1c861eb7bb3fbc9bd418bbff9ad4aa5d0471816258236a31532

## Package layout

- Installs `dkjson.lua` to `share/lua/5.4/dkjson.lua`
- Copies upstream `readme.txt`, which includes the MIT/X11 license text, to
  `licenses/readme.txt`
- Exports `LUA_PATH` through Conan runenv

## Upstream tests

The upstream tarball includes `jsontest.lua`, an official JSON comparison and
regression script. The OHOS upstream run should execute that script with
`LUA_PATH` pointing at the packaged `dkjson.lua`.

## Validation plan

The test package requires `lua/5.4.8.1`, builds a small C program against
`liblua.a`, sets `LUA_PATH`, and executes:

```lua
local json = require('dkjson')
assert(json.version == 'dkjson 2.8')
local encoded = json.encode({hello = 'OHOS', n = 3, nested = {true, false}})
local decoded = json.decode(encoded)
assert(decoded.hello == 'OHOS')
assert(decoded.n == 3)
assert(decoded.nested[1] == true and decoded.nested[2] == false)
```

This verifies the package search path, version metadata, JSON encoding, JSON
decoding, nested array handling, and pretty-print support without adding extra
Lua dependencies.

## Validation results

- Local Windows/MinGW package-only `conan create -tf ''`: passed
- Local package-only full ref: `dkjson/2.8-1#ecfd34b73aeeec2e8dcb8e9cdeaa749e:da39a3ee5e6b4b0d3255bfef95601890afd80709#2448d9d11d3753febc2ccc69b31221fb`
- OHOS new-port run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-dkjson-r2-20260807-070935-16209`
- Full ref: `dkjson/2.8-1#ecfd34b73aeeec2e8dcb8e9cdeaa749e:da39a3ee5e6b4b0d3255bfef95601890afd80709#2448d9d11d3753febc2ccc69b31221fb`
- Consumer smoke: `dkjson smoke ok`
- Gates: L0 pass, L1 pass, L2 skip-no-bin-dir, L4 pass, L5 warn-no-bin-or-lib for pure Lua package
- OHOS upstream run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-dkjson-upstream-r1-20260807-070952-16395`
- Upstream result: `jsontest.lua` rc=0 with packaged `dkjson.lua` first in `LUA_PATH`. The script reports unavailable `de_DE.UTF8` locale as non-fatal output.

## 2026-09-10 fix —— R39 官方 HTTPS 源 + 双 SHA256 核验

R39 要求 conandata 内 URL 必须为官方 HTTPS（CI 会自动为 GitHub URL 添加镜像
fallback，不手动写镜像前缀）。dkolf.de 官方目录同时提供两种官方产物，本次
下载并核验：

- 单文件模块 dkjson-2.8.lua（23790 B）：SHA256
  eb3bf160688fb395a2db6bc52eeff4f7855a6321d2b41bdc754554d13f4e7d44
  —— 任务上游身份锚点所指的官方单文件源码。
- 官方发布归档 dkjson-2.8.tar.gz（17442 B）：SHA256
  24e8cd3beb91c1c861eb7bb3fbc9bd418bbff9ad4aa5d0471816258236a31532
  —— 本配方 source 采用的产物（与 LuaRocks 2.8-1 一致，内含 dkjson.lua、
  jsontest.lua 上游测试与 readme.txt）。

归档与单文件版本号均为 dkjson 2.8（json.version == 'dkjson 2.8' 实测一致）。
选用归档以保留官方 jsontest.lua 上游测试与许可文本；单文件 SHA 一并记录备查。

变更：仅将 URL 协议 http -> https，配方逻辑、测试与依赖保持不变（最小修复）。
