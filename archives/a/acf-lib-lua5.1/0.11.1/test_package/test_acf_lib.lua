local pkg = arg[1]
local harness = arg[2]
assert(pkg and pkg ~= "", "missing package folder")
assert(harness and harness ~= "", "missing test harness folder")

local base = pkg .. "/share/lua/5.1"
local stub = harness .. "/share/lua/5.1"
package.path = table.concat({
  base .. "/?.lua",
  base .. "/?/init.lua",
  base .. "/acf/?.lua",
  stub .. "/?.lua",
  stub .. "/?/init.lua",
  package.path,
}, ";")

local passed, failed = 0, 0
local function check(name, condition)
  if condition then
    passed = passed + 1
    io.write("[PASS] " .. name .. "\n")
  else
    failed = failed + 1
    io.write("[FAIL] " .. name .. "\n")
  end
end

local function exists(path)
  local file = io.open(path, "r")
  if not file then return false end
  file:close()
  return true
end

local modules = {
  "apk", "date", "db", "format", "fs", "html", "processinfo", "validator"
}
for _, module in ipairs(modules) do
  check("packaged acf/" .. module, exists(base .. "/acf/" .. module .. ".lua"))
  check("compat " .. module, exists(base .. "/" .. module .. ".lua"))
end

local loaded = {}
for _, module in ipairs(modules) do
  local ok, value = pcall(require, "acf." .. module)
  loaded[module] = value
  check("require acf." .. module, ok and type(value) == "table")
end

local compat_ok, compat = pcall(require, "format")
check("require compatibility format", compat_ok and type(compat) == "table")

local format = loaded.format
check("format.dostounix",
  type(format) == "table" and type(format.dostounix) == "function" and
  format.dostounix("a\r\nb") == "a\nb")
local escaped
if type(format) == "table" and
    type(format.escapemagiccharacters) == "function" then
  escaped = format.escapemagiccharacters("a.b*c?")
end
check("format.escapemagiccharacters",
  type(escaped) == "string" and escaped:find("%", 1, true) ~= nil)
local formatted_size
if type(format) == "table" and type(format.formatfilesize) == "function" then
  formatted_size = format.formatfilesize(2048)
end
check("format.formatfilesize unit",
  type(formatted_size) == "string" and formatted_size:sub(-1) == "k")
check("format.formatfilesize zero",
  type(format) == "table" and type(format.formatfilesize) == "function" and
  format.formatfilesize(0) == "0")
check("format.cap_begin_word",
  type(format) == "table" and type(format.cap_begin_word) == "function" and
  format.cap_begin_word("hello world") == "Hello World")

local validator = loaded.validator
check("validator.is_string",
  type(validator) == "table" and type(validator.is_string) == "function" and
  validator.is_string("x") and not validator.is_string(1))
check("validator.is_boolean",
  type(validator) == "table" and type(validator.is_boolean) == "function" and
  validator.is_boolean(true) and not validator.is_boolean("x"))
check("validator.is_number",
  type(validator) == "table" and type(validator.is_number) == "function" and
  validator.is_number(3) and not validator.is_number("3"))
check("validator.is_ipv4 valid",
  type(validator) == "table" and type(validator.is_ipv4) == "function" and
  validator.is_ipv4("192.168.0.1") == true)
local valid, message
if type(validator) == "table" and type(validator.is_ipv4) == "function" then
  valid, message = validator.is_ipv4("999.1.1.1")
end
check("validator.is_ipv4 invalid",
  valid == false and message == "Invalid Value")

local discovered = passed + failed
io.write(string.format("ACF_LIB_TEST: %d pass, %d fail\n", passed, failed))
io.write(string.format(
  'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"lua-runner test_acf_lib.lua <pkg> <harness>","discovered":%d,"passedCount":%d}\n',
  failed == 0 and "true" or "false", discovered, passed))
io.stdout:flush()
if failed ~= 0 then error("consumer assertions failed", 0) end
