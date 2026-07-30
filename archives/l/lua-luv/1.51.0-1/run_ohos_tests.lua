-- Execute luv's upstream Lua tests that are supported by the OHOS test host.
local root = assert(os.getenv("LUV_SOURCE_DIR"))
local test_binary = assert(os.getenv("LUV_TEST_BINARY"))

-- src/test.c is an embedding driver, not the Lua CLI, so recreate arg[0].
arg = {[0] = test_binary}
package.path = root .. "/?.lua;" .. package.path

local tap = require("lib/tap")
local uv = require("luv")
local skipped = {
  ["test-dns.lua"] = "requires public DNS resolution; the OHOS CI host returns EINVAL for luvit.io",
  ["test-loop.lua"] = "issue #599 uv.run callback count differs on the OHOS test host",
  ["test-pipe.lua"] = "requires pipe chmod and abstract Unix socket behavior",
  ["test-udp.lua"] = "recvmmsg receives ENOBUFS on the OHOS test host",
}

local request = assert(uv.fs_scandir(root .. "/tests"))
while true do
  local name = uv.fs_scandir_next(request)
  if not name then
    break
  end
  local suite = name:match("^test%-(.*)%.lua$")
  if suite then
    if skipped[name] then
      print("# SKIP " .. name .. ": " .. skipped[name])
    else
      tap(suite)
      dofile(root .. "/tests/" .. name)
    end
  end
end

tap(true)
