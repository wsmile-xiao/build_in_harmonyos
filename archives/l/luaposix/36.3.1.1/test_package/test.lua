assert(_VERSION == 'Lua 5.4', 'expected Lua 5.4, got ' .. tostring(_VERSION))
local cpath = os.getenv('LUA_CPATH') or ''
local package_cpath = cpath:match('^([^;]+)') or ''
assert(package_cpath:find('/lib/lua/5.4/', 1, true), 'LUA_CPATH does not point to Lua 5.4 artifacts')
local artifact, search_error = package.searchpath('posix.signal', package_cpath)
assert(artifact, 'tested package C artifact not found: ' .. tostring(search_error))
local ok, posix = pcall(require, 'posix')
assert(ok, 'posix module failed to load: ' .. tostring(posix))
local signal_ok, signal = pcall(require, 'posix.signal')
assert(signal_ok and type(signal.kill) == 'function', 'posix.signal C module failed to load: ' .. tostring(signal))
local version_ok, version = pcall(require, 'posix.version')
assert(version_ok and version:match('luaposix 36%.3$'),
       'posix.version does not contain upstream version 36.3: ' .. tostring(version))
print('Lua 5.4 loaded posix and posix.signal from the tested package')
