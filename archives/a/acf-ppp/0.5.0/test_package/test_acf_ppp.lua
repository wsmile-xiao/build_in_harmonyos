local app_dir = assert(arg[1], "acf-ppp application directory is required")

local checks = 0
local function check(label, condition)
    checks = checks + 1
    if not condition then
        error("check failed: " .. label, 0)
    end
    io.stdout:write("[ok] ", label, "\n")
end

local function load_packaged(name)
    local chunk, err = loadfile(app_dir .. "/" .. name)
    if not chunk then
        error(err, 0)
    end
    return chunk()
end

local file_reads = {}
package.preload["modelfunctions"] = function()
    return {
        getfiledetails = function(path, allowed)
            file_reads[#file_reads + 1] = { path = path, allowed = allowed }
            return { path = path }
        end,
        setfiledetails = function(_, details)
            return details
        end,
    }
end
package.preload["acf.processinfo"] = function()
    return {
        package_version = function(name)
            return "2.5.2", name == "ppp" and nil or "wrong package"
        end,
        pidof = function(name)
            return name == "pppd" and { 42 } or {}
        end,
    }
end
package.preload["acf.fs"] = function()
    return {
        find_files_as_array = function(_, path)
            if path == "/etc/ppp/peers/" then
                return { path .. "provider" }
            end
            return {}
        end,
    }
end
package.preload["acf.validator"] = function()
    return { is_valid_filename = function() return true end }
end

function cfe(value)
    return value
end

local model = load_packaged("ppp-model.lua")
check("model returns a module table", type(model) == "table")

local status = model.getstatus()
check("status reports the ppp package version",
      status.value.version.value == "2.5.2")
check("status detects the pppd process",
      status.value.status.value == "Started")

local peers = model.list_peers()
check("peer listing uses /etc/ppp/peers",
      peers.value[1] == "/etc/ppp/peers/provider")

local pap = model.read_papfiledetails()
local chap = model.read_chapfiledetails()
check("PAP configuration path is correct",
      pap.path == "/etc/ppp/pap-secrets")
check("CHAP configuration path is correct",
      chap.path == "/etc/ppp/chap-secrets")
check("both authentication files were requested", #file_reads == 2)

local controller = load_packaged("ppp-controller.lua")
check("controller default action is status",
      controller.default_action == "status")

local ctx = { model = model }
local dispatched = controller.status(ctx)
check("controller status dispatches to the packaged model",
      dispatched.value.status.value == "Started")

io.stdout:write(string.format("acf-ppp functional checks: %d passed\n", checks))
