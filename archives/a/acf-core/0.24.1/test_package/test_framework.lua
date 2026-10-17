-- test_framework.lua — functional verification of the packaged acf-core.
-- Loads the REAL acf.mvc framework, reads a config (exercising read_config),
-- builds the acf_cli application and dispatches the safe acf-util/welcome/read
-- action, verifying the full framework call chain (R34).
-- Usage: lua-runner test_framework.lua <acf-core-package-folder>
local pkg = arg[1]
assert(pkg and pkg ~= "", "usage: test_framework.lua <pkg-folder>")

local base = pkg .. "/share"
local home = arg[2] or "test-home"
local pass, fail = 0, 0
local function check(name, cond)
  if cond then pass = pass + 1; io.write("[PASS] " .. name .. "\n")
  else fail = fail + 1; io.write("[FAIL] " .. name .. "\n") end
end

-- Sanity: package layout
local function exists(f)
  local fh = io.open(f, "r")
  if fh then fh:close(); return true end
  return false
end
check("packaged share/lua/5.4/acf/mvc.lua", exists(base .. "/lua/5.4/acf/mvc.lua"))
check("packaged share/acf/lib/session.lua", exists(base .. "/acf/lib/session.lua"))
check("packaged share/acf/app/acf_www-controller.lua", exists(base .. "/acf/app/acf_www-controller.lua"))
check("packaged bin/acf-cli", exists(pkg .. "/bin/acf-cli"))
check("packaged bin/acfpasswd", exists(pkg .. "/bin/acfpasswd"))

-- Load the real framework module
local mvc = require("acf.mvc")
check("require(acf.mvc)", type(mvc) == "table")

local FRAMEWORK = mvc:new()
FRAMEWORK:read_config("acf", home)
check("read_config sets appdir", type(FRAMEWORK.conf.appdir) == "string"
      and #FRAMEWORK.conf.appdir > 0)

local APP = FRAMEWORK:new("acf_cli")
local okd, errd = pcall(function()
  return APP:dispatch("/acf-util/", "welcome", "read", { viewtype = "serialized" })
end)
check("dispatch acf-util/welcome/read ok", okd)
if not okd then io.write("    dispatch error: " .. tostring(errd) .. "\n") end

-- session.serialize is the CLI output serializer used by acf-cli
local session = require("session")
local s = session.serialize("result", { self = "acf-core", n = 42 })
check("session.serialize works", type(s) == "string" and #s > 0)

FRAMEWORK:destroy()

io.write(string.format("FRAMEWORK_TEST: %d pass, %d fail\n", pass, fail))
os.exit(fail == 0 and 0 or 1)
