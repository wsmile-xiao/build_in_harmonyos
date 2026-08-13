#!/data/service/hnp/bin/bash
set -euo pipefail
echo "=== luaposix test ==="
# R34: 测试必须真实依赖被测包制品。luaposix 主模块 posix 是纯 Lua 的
# posix/init.lua（走 LUA_PATH），仅 require('posix') 在制品缺失时仍可能
# 通过；因此显式加载包内 C 子模块 posix.signal（走 LUA_CPATH →
# lib/lua/5.5/posix/signal.so），使负面测试（lib/ 被移走）必然失败。
lua -e "
local cpath = os.getenv('LUA_CPATH') or ''
local seg = cpath:match('^([^;]+)') or ''
assert(seg ~= '', 'LUA_CPATH not provided by package')
local ok, posix = pcall(require, 'posix')
assert(ok, 'posix module failed to load: ' .. tostring(posix))
local sok, sig = pcall(require, 'posix.signal')
assert(sok, 'posix.signal (C artifact) failed to load: ' .. tostring(sig))
print('posix module + posix.signal C artifact loaded from package')
"
echo "luaposix OK"
