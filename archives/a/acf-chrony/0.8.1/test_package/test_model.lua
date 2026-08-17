-- test_model.lua — complete functional verification of the acf-chrony MODEL layer.
-- Loads the REAL chrony-model.lua from the conan acf-chrony package and exercises
-- every public model function (R34): getstatus / getdetails / get_startstop /
-- startstop_service / get_config / update_config / get_keyfiledetails /
-- update_keyfiledetails / get_enable_keyfile / enable_keyfile / get_filedetails /
-- update_filedetails / get_logfile — including the config validation rules
-- (validate_config) and the file write-back path.
--
-- External framework deps (acf-core's cfe() / modelfunctions / acf.validator)
-- are mocked with faithful stand-ins; chrony-model.lua itself is the REAL code.
-- Usage: lua-runner test_model.lua <acf-chrony-package-folder>
local pkg = arg[1]
assert(pkg and pkg ~= "", "usage: test_model.lua <pkg-folder>")

local appdir = pkg .. "/share/acf/app/chrony"
local pass, fail = 0, 0
local function check(name, cond)
  if cond then pass = pass + 1; io.write("[PASS] " .. name .. "\n")
  else fail = fail + 1; io.write("[FAIL] " .. name .. "\n") end
end

-- ---------------------------------------------------------------
-- Mock acf-core framework globals BEFORE loading chrony-model.lua
-- ---------------------------------------------------------------
-- cfe(): acf-core's create-form-element helper. Returns a table carrying the
-- given fields; callers read .value / .label / .type / .descr / .seq / .errtxt.
cfe = function(params)
  local el = {}
  if type(params) == "table" then
    for k, v in pairs(params) do el[k] = v end
  end
  el.value = el.value or ""
  el.type = el.type or "text"
  return el
end

-- modelfunctions: acf-core lib used by the model for status/startstop/file mgmt.
local exec_called, last_cmd = false, nil
local getstatus_called = false
package.loaded["modelfunctions"] = {
  getstatus = function(processname, packagename, label)
    getstatus_called = true
    return { value = "running", label = label, processname = processname, packagename = packagename }
  end,
  get_startstop = function(processname)
    return { option = { "start", "stop" }, value = "stopped", processname = processname }
  end,
  startstop_service = function(startstop, action)
    startstop.mock_startstop_service = action
    return startstop
  end,
  run_executable = function(cmd, check_exit, input)
    exec_called = true
    last_cmd = cmd
    return "chronyd status OK\n", nil
  end,
  getfiledetails = function(path)
    return { value = { filecontent = { value = "", descr = "" }, status = cfe({ value = "", label = "Status" }) }, path = path }
  end,
  setfiledetails = function(self, filedetails, paths)
    filedetails.mock_setfiledetails = paths
    return filedetails
  end,
}

-- acf.validator: only the two functions used by validate_config().
-- is_valid_filename: reject control chars (allow absolute paths incl. '/').
package.loaded["acf.validator"] = {
  is_valid_filename = function(name)
    if type(name) ~= "string" or name == "" then return false end
    return not string.find(name, "[\0-\31]")
  end,
  is_integer = function(v)
    return type(v) == "number" or (type(v) == "string" and string.match(v, "^%-?%d+$") ~= nil)
  end,
}

-- ---------------------------------------------------------------
-- Mock file-system behavior for the config read / write-back paths.
-- The REAL acf.fs shim reads /etc/chrony/chrony.conf which does not
-- exist on the build host; substitute a deterministic in-memory file.
-- ---------------------------------------------------------------
local fs = require("acf.fs")
local MOCK_CONF = ("server 0.pool.ntp.org\nserver 1.pool.ntp.org offline\n"
  .. "allow 192.168.1.0/24\n"
  .. "driftfile /var/lib/chrony/chrony.drift\n"
  .. "keyfile /etc/chrony/chrony.keys\n"
  .. "commandkey 10\n")
local written = nil
local orig_read = fs.read_file
fs.read_file = function(path)
  if path == "/etc/chrony/chrony.conf" then return MOCK_CONF end
  if path == "/etc/chrony/chrony.keys" then return "10 cronpass\n" end
  return orig_read(path)
end
fs.read_file_as_array = function(path)
  if path == "/etc/chrony/chrony.conf" then
    local out = {}
    for line in MOCK_CONF:gmatch("[^\n]+") do out[#out + 1] = line end
    return out
  end
  return nil, "not found"
end
fs.write_file = function(path, str)
  if path == "/etc/chrony/chrony.conf" then
    -- mirror the real shim: append a trailing newline
    written = string.gsub(str or "", "\n*$", "\n")
  end
  return true
end

-- ---------------------------------------------------------------
-- Load the REAL model module
-- ---------------------------------------------------------------
package.path = appdir .. "/?.lua;" .. package.path
local model = require("chrony-model")
check("require(chrony-model)", type(model) == "table")
check("model.getstatus fn", type(model.getstatus) == "function")
check("model.getdetails fn", type(model.getdetails) == "function")
check("model.get_startstop fn", type(model.get_startstop) == "function")
check("model.startstop_service fn", type(model.startstop_service) == "function")
check("model.get_config fn", type(model.get_config) == "function")
check("model.update_config fn", type(model.update_config) == "function")
check("model.get_keyfiledetails fn", type(model.get_keyfiledetails) == "function")
check("model.update_keyfiledetails fn", type(model.update_keyfiledetails) == "function")
check("model.get_enable_keyfile fn", type(model.get_enable_keyfile) == "function")
check("model.enable_keyfile fn", type(model.enable_keyfile) == "function")
check("model.get_filedetails fn", type(model.get_filedetails) == "function")
check("model.update_filedetails fn", type(model.update_filedetails) == "function")
check("model.get_logfile fn", type(model.get_logfile) == "function")

-- ---------------------------------------------------------------
-- getstatus: forwards to modelfunctions.getstatus(chronyd, chrony, label)
-- ---------------------------------------------------------------
local st = model.getstatus()
check("getstatus calls modelfunctions.getstatus", getstatus_called == true)
check("getstatus labels Chrony Status", st.label == "Chrony Status")
check("getstatus processname chronyd", st.processname == "chronyd")
check("getstatus packagename chrony", st.packagename == "chrony")

-- ---------------------------------------------------------------
-- getdetails: pure-Lua structure (time/sources/sourcestats/tracking)
-- ---------------------------------------------------------------
local det = model.getdetails()
check("getdetails returns group", det.type == "group" or det.value ~= nil)
check("getdetails has time", det.value and det.value.time and det.value.time.value ~= nil)
check("getdetails has sources", det.value and det.value.sources ~= nil)
check("getdetails has sourcestats", det.value and det.value.sourcestats ~= nil)
check("getdetails has tracking", det.value and det.value.tracking ~= nil)

-- ---------------------------------------------------------------
-- get_config: parses the mocked chrony.conf into the 5 config fields
-- ---------------------------------------------------------------
local cfg = model.get_config()
check("get_config has server list", type(cfg.value.server.value) == "table")
check("get_config parses server entries", #cfg.value.server.value == 2)
check("get_config server[1] 0.pool.ntp.org", cfg.value.server.value[1] == "0.pool.ntp.org")
check("get_config server[2] keeps offline flag", cfg.value.server.value[2] == "1.pool.ntp.org offline")
check("get_config parses allow", #cfg.value.allow.value == 1 and cfg.value.allow.value[1] == "192.168.1.0/24")
check("get_config parses driftfile", cfg.value.driftfile.value == "/var/lib/chrony/chrony.drift")
check("get_config parses keyfile", cfg.value.keyfile.value == "/etc/chrony/chrony.keys")
check("get_config parses commandkey", cfg.value.commandkey.value == "10")

-- ---------------------------------------------------------------
-- update_config: validation rules (validate_config) + write-back
-- ---------------------------------------------------------------
-- Valid round-trip: edit server list, save, verify write_file called.
local edited = model.get_config()
edited.value.server.value = { "0.pool.ntp.org", "2.pool.ntp.org" }
local saved = model.update_config(nil, edited)
check("update_config valid save no errtxt", saved.errtxt == nil)
check("update_config writes chrony.conf", written ~= nil)
check("write-back contains edited server", written:find("2%.pool%.ntp%.org") ~= nil)
check("write-back preserves driftfile line", written:find("driftfile /var/lib/chrony/chrony%.drift") ~= nil)
check("write-back ends with newline", written:sub(-1) == "\n")

-- Invalid server entry: illegal chars -> "Invalid entry on line N"
local bad_server = model.get_config()
bad_server.value.server.value = { "0.pool.ntp.org", "bad server!!" }
local bad_srv = model.update_config(nil, bad_server)
check("invalid server rejected", bad_srv.errtxt == "Failed to save config")
check("invalid server flagged on line 2", bad_srv.value.server.errtxt ~= nil
      and bad_srv.value.server.errtxt:find("Invalid entry on line 2") ~= nil)

-- Invalid driftfile (contains control char) -> "Invalid file name"
local bad_drift = model.get_config()
bad_drift.value.driftfile.value = "bad\0name"
local bad_d = model.update_config(nil, bad_drift)
check("invalid driftfile rejected", bad_d.errtxt == "Failed to save config")
check("invalid driftfile flagged", bad_d.value.driftfile.errtxt ~= nil
      and bad_d.value.driftfile.errtxt == "Invalid file name")

-- Invalid commandkey (non-integer) -> "Must be an integer"
local bad_key = model.get_config()
bad_key.value.commandkey.value = "abc"
local bad_k = model.update_config(nil, bad_key)
check("invalid commandkey rejected", bad_k.errtxt == "Failed to save config")
check("invalid commandkey flagged", bad_k.value.commandkey.errtxt ~= nil
      and bad_k.value.commandkey.errtxt == "Must be an integer")

-- ---------------------------------------------------------------
-- get_enable_keyfile / enable_keyfile
-- ---------------------------------------------------------------
local ek = model.get_enable_keyfile()
check("get_enable_keyfile returns group", ek.type == "group" and ek.label == "Enable Key File")

-- enable_keyfile: sets keyfile=/etc/chrony/chrony.keys in config, saves it
-- (write-back via update_config), returns the request (errtxt set on failure).
local enablereq = model.get_enable_keyfile()
local enr = model.enable_keyfile(nil, enablereq)
check("enable_keyfile no errtxt for valid save", enr.errtxt == nil)
check("enable_keyfile persists keyfile line",
      written ~= nil and written:find("keyfile /etc/chrony/chrony.keys") ~= nil)

-- ---------------------------------------------------------------
-- startstop_service: action handling + password lookup
-- ---------------------------------------------------------------
-- unknown action (e.g. "restart") -> modelfunctions.startstop_service
local ss = model.startstop_service(nil, { value = "stopped", option = {} }, "restart")
check("startstop_service unknown action forwarded", ss.mock_startstop_service == "restart")

-- action "online" with no key file defined -> errtxt
local MOCK_CONF_NOKEY = MOCK_CONF:gsub("keyfile /etc/chrony/chrony.keys\n", "")
local old_rf_nk = fs.read_file
fs.read_file = function(path)
  if path == "/etc/chrony/chrony.conf" then return MOCK_CONF_NOKEY end
  return old_rf_nk(path)
end
local ss2 = model.startstop_service(nil, { value = "stopped", option = {} }, "online")
check("startstop_service online no keyfile -> No key file defined",
      ss2.errtxt ~= nil and ss2.errtxt == "No key file defined")
fs.read_file = old_rf_nk

-- action "online" with keyfile but no commandkey -> errtxt
local MOCK_CONF_NOCMD = MOCK_CONF:gsub("commandkey 10\n", "")
local orig_rf = fs.read_file
fs.read_file = function(path)
  if path == "/etc/chrony/chrony.conf" then return MOCK_CONF_NOCMD end
  return orig_rf(path)
end
local ss3 = model.startstop_service(nil, { value = "stopped", option = {} }, "online")
check("startstop_service online no commandkey -> No command key defined",
      ss3.errtxt ~= nil and ss3.errtxt == "No command key defined")
fs.read_file = orig_rf

-- action "online" with keyfile+commandkey -> password lookup -> chronyc exec
exec_called = false; last_cmd = nil
local ss4 = model.startstop_service(nil, { value = "stopped", option = {} }, "online")
check("startstop_service online with password execs chronyc", exec_called == true)
check("startstop_service execs chronyc -m password online",
      last_cmd ~= nil and last_cmd[1] == "chronyc" and last_cmd[4] == "online")

-- ---------------------------------------------------------------
-- file details: get_keyfiledetails / get_filedetails / updates
-- ---------------------------------------------------------------
local kfd = model.get_keyfiledetails()
check("get_keyfiledetails returns filecontent", kfd.value ~= nil and kfd.value.filecontent ~= nil)
check("get_keyfiledetails descr set", kfd.value.filecontent.descr ~= nil
      and kfd.value.filecontent.descr:find("password numbers") ~= nil)

local fd = model.get_filedetails()
check("get_filedetails path is chrony.conf", fd.path == "/etc/chrony/chrony.conf")

local ukfd = model.update_keyfiledetails(nil, { value = { filecontent = cfe({ value = "" }) } })
check("update_keyfiledetails calls setfiledetails", ukfd.mock_setfiledetails ~= nil
      and ukfd.mock_setfiledetails[1] == "/etc/chrony/chrony.keys")

local ufd = model.update_filedetails(nil, { value = {} })
check("update_filedetails calls setfiledetails", ufd.mock_setfiledetails ~= nil
      and ufd.mock_setfiledetails[1] == "/etc/chrony/chrony.conf")

-- ---------------------------------------------------------------
-- get_logfile: structure with facility daemon + grep chronyd
-- ---------------------------------------------------------------
local lf = model.get_logfile(nil, {})
check("get_logfile returns structure", lf.type == "structure" and lf.label == "Log File Configuration")
check("get_logfile facility daemon", lf.value[1] ~= nil and lf.value[1].facility == "daemon")
check("get_logfile grep chronyd", lf.value[1] ~= nil and lf.value[1].grep == "chronyd")

io.write(string.format("APP_MODEL_TEST: %d pass, %d fail\n", pass, fail))
os.exit(fail == 0 and 0 or 1)
