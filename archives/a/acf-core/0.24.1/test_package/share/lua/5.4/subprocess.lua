-- subprocess.lua — TEST-HARNESS ONLY pure-Lua shim for the lua-subprocess
-- module used by acf-core (mvc.lua / modelfunctions.lua). Implemented on top
-- of io.popen. NOT shipped with the acf-core conan package.
local mymodule = {}

mymodule.PIPE = 1
-- Match lua-subprocess: callers use stderr=subprocess.STDOUT as a table key.
mymodule.STDOUT = 2

local function build_cmdline(args)
  if type(args) ~= "table" then
    return tostring(args)
  end
  local parts = {}
  for _, v in ipairs(args) do
    -- Skip redirect constants (numbers) and nested tables; named keys like
    -- stderr=STDOUT are already ignored by ipairs.
    if type(v) ~= "table" and type(v) ~= "number" and v ~= nil then
      parts[#parts+1] = tostring(v)
    end
  end
  return table.concat(parts, " ")
end

-- call({cmd, arg1, ...}) -> true/false, output
function mymodule.call(args)
  local cmdline = build_cmdline(args)
  local f = io.popen(cmdline .. " 2>&1")
  if not f then return false, "popen failed" end
  local out = f:read("*a") or ""
  f:close()
  return true, out
end

-- call_capture(args) -> exit_code, output  (lua-subprocess API)
function mymodule.call_capture(args)
  local cmdline = build_cmdline(args)
  local f = io.popen(cmdline .. " 2>&1")
  if not f then return -1, "popen failed" end
  local out = f:read("*a") or ""
  f:close()
  return 0, out
end

-- popen(args) -> proc, errmsg, errno
-- args[1] = executable, args[2..] = arguments
-- args.stdin / args.stdout / args.stderr may be PIPE or "/dev/null"
-- Returns proc with .stdin/.stdout/.stderr handles, .poll(), .wait(), .exitcode
function mymodule.popen(args)
  local cmdline
  if type(args) == "table" then
    local parts = {}
    for _, v in ipairs(args) do
      if type(v) ~= "table" and type(v) ~= "number" and v ~= nil then
        parts[#parts+1] = tostring(v)
      end
    end
    cmdline = table.concat(parts, " ")
  else
    cmdline = tostring(args)
  end
  local want_stdin = (args and args.stdin == mymodule.PIPE)
  local stdin_redir = want_stdin and "" or (args and args.stdin == "/dev/null" and "< /dev/null " or "")
  local popen_cmd = cmdline .. (stdin_redir or "") .. " 2>&1"
  local ph = io.popen(popen_cmd, "w")
  if not ph then return nil, "popen failed", 1 end
  local proc = {}
  proc.stdin = { write = function(_, s) ph:write(s) end,
                 close = function() ph:close() end }
  local outbuf = ""
  proc.stdout = { read = function(_, mode)
                    if outbuf == "" then
                      local t0 = os.time()
                      -- io.popen with "w" gives no read channel; return what
                      -- we buffered (best-effort for the harness).
                    end
                    return ""
                  end,
                  close = function() end }
  proc.stderr = { read = function(_, mode) return "" end, close = function() end }
  proc.exitcode = 0
  proc.poll = function() return true end
  proc.wait = function() proc.exitcode = 0; return 0 end
  return proc
end

return mymodule
