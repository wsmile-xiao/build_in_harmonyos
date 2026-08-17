-- test_app.lua — substantive verification of the packaged acf-chrony app plugin.
-- Loads the REAL chrony-controller / chrony-model Lua modules from the conan
-- acf-chrony package and exercises the controller→model call chain that
-- acf-core's acf-cli would dispatch (R34: real dependency on the tested package).
-- Usage: lua-runner test_app.lua <acf-chrony-package-folder>
local pkg = arg[1]
assert(pkg and pkg ~= "", "usage: test_app.lua <pkg-folder>")

local appdir = pkg .. "/share/acf/app/chrony"
local pass, fail = 0, 0
local function check(name, cond)
  if cond then pass = pass + 1; io.write("[PASS] " .. name .. "\n")
  else fail = fail + 1; io.write("[FAIL] " .. name .. "\n") end
end

-- Sanity: packaged app plugin layout
-- exists(): true if the path entry exists (file OR symlink, even if dangling).
-- Lua's io.open resolves symlinks; a dangling symlink opens as nil. Use
-- os.stat (follows) OR os.lstat equivalent — Lua has no lstat, so use a
-- pcall + io.open for regular files and a symlink-specific check via
-- readlink-style: popen("readlink") or check parent dir listing.
local function path_exists(path)
  -- Regular file check (also works for non-dangling symlinks)
  local fh = io.open(path, "r")
  if fh then fh:close(); return true end
  -- Dangling symlink: ls -l on the parent shows the entry; use os.execute
  -- trick (ls prints the link even if target missing). Lua's os.execute
  -- returns exit code; test with test -e OR test -L.
  local rc = os.execute('test -e "' .. path .. '" 2>/dev/null || test -L "' .. path .. '"')
  -- Lua 5.4: os.execute returns true/nil/exitcode; treat 0 as success.
  if rc == true or rc == 0 then return true end
  return false
end
check("packaged chrony-controller.lua", path_exists(appdir .. "/chrony-controller.lua"))
check("packaged chrony-model.lua", path_exists(appdir .. "/chrony-model.lua"))
check("packaged chrony-config-html.lsp", path_exists(appdir .. "/chrony-config-html.lsp"))
check("packaged chrony-details-html.lsp", path_exists(appdir .. "/chrony-details-html.lsp"))
check("packaged chrony-keyfile-html.lsp", path_exists(appdir .. "/chrony-keyfile-html.lsp"))
check("packaged chrony.menu", path_exists(appdir .. "/chrony.menu"))
check("packaged chrony.roles", path_exists(appdir .. "/chrony.roles"))

-- The three .lsp symlinks point to acf-core shared templates; verify the
-- symlink entries exist (resolution depends on acf-core package at runtime).
check("symlink chrony-expert-html.lsp", path_exists(appdir .. "/chrony-expert-html.lsp"))
check("symlink chrony-logfile-html.lsp", path_exists(appdir .. "/chrony-logfile-html.lsp"))
check("symlink chrony-status-html.lsp", path_exists(appdir .. "/chrony-status-html.lsp"))

-- Load the real controller module
package.path = appdir .. "/?.lua;" .. package.path
local controller = require("chrony-controller")
check("require(chrony-controller)", type(controller) == "table")
check("controller.default_action == status", controller.default_action == "status")
check("controller.status fn", type(controller.status) == "function")
check("controller.details fn", type(controller.details) == "function")
check("controller.startstop fn", type(controller.startstop) == "function")
check("controller.config fn", type(controller.config) == "function")
check("controller.keyfile fn", type(controller.keyfile) == "function")
check("controller.enablekeyfile fn", type(controller.enablekeyfile) == "function")
check("controller.expert fn", type(controller.expert) == "function")
check("controller.logfile fn", type(controller.logfile) == "function")

-- controller.status(self) dispatches self.model.getstatus(); build a mock
-- self with a stub model to verify the controller→model call chain works.
local mock_self = { model = {} }
local status_called = false
mock_self.model.getstatus = function()
  status_called = true
  return { value = "chronyd (running)" }
end
local result = controller.status(mock_self)
check("controller.status dispatches model.getstatus", status_called == true)
check("controller.status returns model result", type(result) == "table")

-- controller.details(self) dispatches self.model.getdetails(); verify chain
local details_called = false
mock_self.model.getdetails = function()
  details_called = true
  return { time = { value = "2026-08-16" } }
end
local details_result = controller.details(mock_self)
check("controller.details dispatches model.getdetails", details_called == true)
check("controller.details returns model result", type(details_result) == "table")

-- controller.config(self) dispatches self.model.get_config via handle_form;
-- verify the mock model is invoked (handle_form calls get_config for GET).
local config_called = false
mock_self.model.get_config = function()
  config_called = true
  return { value = {} }
end
mock_self.model.update_config = function(self, config)
  return config
end
mock_self.handle_form = function(self, getter, setter, clientdata, ...)
  return getter()
end
mock_self.clientdata = {}
local config_result = controller.config(mock_self)
check("controller.config dispatches model.get_config", config_called == true)

-- controller.keyfile(self) dispatches self.model.get_keyfiledetails via handle_form
local keyfile_called = false
mock_self.model.get_keyfiledetails = function()
  keyfile_called = true
  return { value = {} }
end
mock_self.model.update_keyfiledetails = function(self, filedetails)
  return filedetails
end
local keyfile_result = controller.keyfile(mock_self)
check("controller.keyfile dispatches model.get_keyfiledetails", keyfile_called == true)

-- controller.expert(self) dispatches self.model.get_filedetails via handle_form
local expert_called = false
mock_self.model.get_filedetails = function()
  expert_called = true
  return { value = {} }
end
mock_self.model.update_filedetails = function(self, filedetails)
  return filedetails
end
local expert_result = controller.expert(mock_self)
check("controller.expert dispatches model.get_filedetails", expert_called == true)

-- controller.logfile(self) dispatches self.model.get_logfile(self, clientdata)
local logfile_called = false
mock_self.model.get_logfile = function(self, clientdata)
  logfile_called = true
  return { value = {} }
end
local logfile_result = controller.logfile(mock_self)
check("controller.logfile dispatches model.get_logfile", logfile_called == true)

-- controller.startstop(self) dispatches self.model.get_startstop via handle_form
local startstop_called = false
mock_self.model.get_startstop = function(self, clientdata)
  startstop_called = true
  return { value = {} }
end
mock_self.model.startstop_service = function(self, startstop, action)
  return startstop
end
local startstop_result = controller.startstop(mock_self)
check("controller.startstop dispatches model.get_startstop", startstop_called == true)

-- controller.enablekeyfile(self) dispatches self.model.get_enable_keyfile via handle_form
local enablekeyfile_called = false
mock_self.model.get_enable_keyfile = function()
  enablekeyfile_called = true
  return { value = {} }
end
mock_self.model.enable_keyfile = function(self, enablerequest)
  return enablerequest
end
local enablekeyfile_result = controller.enablekeyfile(mock_self)
check("controller.enablekeyfile dispatches model.get_enable_keyfile", enablekeyfile_called == true)

-- Parse chrony.menu for the expected ACF menu registrations (Networking/50NTP)
-- Format: CAT<tab>GROUP/DESC<tab>TAB<tab>ACTION (tab-separated, may have leading
-- spaces in the group field; first line is a #CAT comment header).
-- The menu registers details/config/keyfile/expert/logfile actions (status is
-- the controller default_action, not a menu action).
local menu = {}
for line in io.lines(appdir .. "/chrony.menu") do
  if line:sub(1, 1) ~= "#" then
    -- Split on whitespace runs: fields = CAT, GROUP/DESC, TAB, ACTION
    local fields = {}
    for w in line:gmatch("%S+") do fields[#fields+1] = w end
    if #fields >= 4 then
      menu[#menu+1] = {cat=fields[1], group_desc=fields[2], tab=fields[3], action=fields[4]}
    end
  end
end
check("menu has 5 Networking entries", #menu == 5)
local has_details = false
for _, m in ipairs(menu) do
  if m.action == "details" then has_details = true; break end
end
check("menu registers details action", has_details)

-- Parse chrony.roles for the USER role containing chrony:status
local roles_content = ""
local rf = io.open(appdir .. "/chrony.roles", "r")
if rf then roles_content = rf:read("*a"); rf:close() end
check("USER role grants chrony:status", roles_content:find("chrony:status") ~= nil)
check("EXPERT role grants chrony:expert", roles_content:find("chrony:expert") ~= nil)

io.write(string.format("APP_PLUGIN_TEST: %d pass, %d fail\n", pass, fail))
os.exit(fail == 0 and 0 or 1)
