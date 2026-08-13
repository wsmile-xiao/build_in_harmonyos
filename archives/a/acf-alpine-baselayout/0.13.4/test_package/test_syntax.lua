-- test_syntax.lua — syntax-load every packaged .lua file with the REAL Lua 5.4
-- runtime (mini_lua runner linked against conan lua/5.4.8). loadfile() only
-- compiles; the module-level require() calls are NOT executed, so this
-- validates syntax of the packaged app without needing the full ACF runtime.
-- Usage: lua-runner test_syntax.lua <app-dir>
local dir = arg[1]
assert(dir and dir ~= "", "usage: test_syntax.lua <app-dir>")

local function list_lua_files(d)
  local files = {}
  local p = io.popen("find \"" .. d .. "\" -name '*.lua' -type f 2>/dev/null | sort")
  if not p then return files end
  for line in p:lines() do
    files[#files + 1] = line
  end
  p:close()
  return files
end

local files = list_lua_files(dir)
local pass, fail = 0, 0
for _, f in ipairs(files) do
  local ok, err = loadfile(f)
  if ok then
    pass = pass + 1
    io.write("[PASS] syntax " .. f .. "\n")
  else
    fail = fail + 1
    io.write("[FAIL] syntax " .. f .. ": " .. tostring(err) .. "\n")
  end
end

io.write(string.format("SYNTAX_TEST: %d pass, %d fail (%d files)\n", pass, fail, #files))
os.exit(fail == 0 and 0 or 1)
