local app_dir = arg[1]
local config_file = arg[2]
assert(app_dir and config_file, "usage: test.lua <app-dir> <config-file>")

local passed = 0
local function check(name, condition)
  assert(condition, name)
  passed = passed + 1
  io.write("[PASS] " .. name .. "\n")
end

local function read_file(path)
  local file = assert(io.open(path, "rb"))
  local value = file:read("*a")
  file:close()
  return value
end

local function write_file(path, value)
  local file = assert(io.open(path, "wb"))
  file:write(value)
  file:close()
end

-- cfe is supplied by the ACF host. This constructor preserves its table
-- contract while all required modules below come from Conan dependencies.
_G.cfe = function(value) return value end

local posix = require("posix")
local subprocess = require("subprocess")
local modelfunctions = require("modelfunctions")
local validator = require("acf.validator")
local fs = require("acf.fs")
local format = require("acf.format")
check("real luaposix loaded", type(posix) == "table")
check("real lua-subprocess loaded", type(subprocess) == "table")
check("real acf-core modelfunctions loaded", type(modelfunctions) == "table")
check("real acf-lib validator loaded", type(validator.is_port) == "function")
check("real acf-lib fs loaded", type(fs.read_file) == "function")
check("real acf-lib format loaded", type(format.parse_configfile) == "function")

local controller = assert(loadfile(app_dir .. "/openssh-controller.lua"))()
check("controller default action", controller.default_action == "status")
for _, action in ipairs({
  "status", "config", "startstop", "expert", "connectedpeers",
  "listusers", "listauth", "deleteauth", "addauth", "logfile"
}) do
  check("controller exports " .. action, type(controller[action]) == "function")
end

write_file(config_file, table.concat({
  "#Port 22",
  "Port 2200",
  "ListenAddress 127.0.0.1",
  "PermitRootLogin no",
  "PasswordAuthentication no",
  "UseDNS yes",
  "SyslogFacility AUTHPRIV",
  ""
}, "\n"))

local model = assert(loadfile(app_dir .. "/openssh-model.lua"))()
local config = model.read_config()
check("read Port", tostring(config.value.Port.value) == "2200")
check("read ListenAddress", config.value.ListenAddress.value == "127.0.0.1")
check("read PermitRootLogin", config.value.PermitRootLogin.value == "no")
check("read PasswordAuthentication", config.value.PasswordAuthentication.value == false)
check("read UseDNS", config.value.UseDNS.value == true)

local original = read_file(config_file)
config.value.ListenAddress.value = "999.1.1.1"
config.value.Port.value = "70000"
local rejected = model.update_config(nil, config)
check("invalid address rejected", rejected.value.ListenAddress.errtxt == "Invalid IP")
check("invalid port rejected", rejected.value.Port.errtxt == "Invalid Port")
check("invalid update does not write", read_file(config_file) == original)

config = model.read_config()
config.value.Port.value = "2222"
config.value.ListenAddress.value = "0.0.0.0"
config.value.PermitRootLogin.value = "prohibit-password"
config.value.PasswordAuthentication.value = true
config.value.UseDNS.value = false
local updated = model.update_config(nil, config)
check("valid update succeeds", updated.errtxt == nil)
local saved = read_file(config_file)
check("updated Port persisted", saved:find("Port 2222", 1, true) ~= nil)
check("updated ListenAddress persisted", saved:find("ListenAddress 0.0.0.0", 1, true) ~= nil)
check("boolean true persisted", saved:find("PasswordAuthentication yes", 1, true) ~= nil)
check("boolean false persisted", saved:find("UseDNS no", 1, true) ~= nil)

local logfile = model.get_logfile(nil, {})
check("SyslogFacility parsed", logfile.value.facility.value == "authpriv")
check("config path came from environment", os.getenv("ACF_OPENSSH_CONFIG") == config_file)

io.write(string.format("ACF_OPENSSH_TEST: %d checks passed\n", passed))
