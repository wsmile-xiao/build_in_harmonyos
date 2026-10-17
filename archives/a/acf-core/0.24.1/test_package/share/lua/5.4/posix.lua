-- posix.lua — TEST-HARNESS ONLY pure-Lua shim for the POSIX Lua module.
-- Implements the subset of the posix module API used by acf-core's Lua
-- framework (mvc.lua, session.lua, lib/*.lua). NOT shipped with the
-- acf-core conan package; exists solely so the real framework code can be
-- executed by the Lua 5.4 interpreter during verification.
local mymodule = {}

-- track setenv/getenv in-process (real setenv requires a C module)
local _env = {}
function mymodule.setenv(name, value, overwrite)
  if overwrite == nil or overwrite ~= false then
    _env[name] = value
  elseif _env[name] == nil then
    _env[name] = value
  end
end
function mymodule.getenv(name)
  if _env[name] ~= nil then return _env[name] end
  return os.getenv(name)
end

function mymodule.getpid()
  return 12345
end

function mymodule.basename(path)
  path = path or ""
  if type(path) ~= "string" then path = tostring(path) end
  return string.gsub(path, "(.*[/\\])", "")
end

function mymodule.dirname(path)
  path = path or ""
  if type(path) ~= "string" then path = tostring(path) end
  if not string.find(path, "[/\\]") then return "." end
  local dir = string.gsub(path, "(.*[/\\])[^/\\]*[/\\]?$", "%1")
  dir = string.gsub(dir, "[/\\]+$", "")
  if dir == "" then return "." end
  return dir
end

function mymodule.glob(pattern)
  local out = {}
  local f = io.popen("ls -1 " .. pattern .. " 2>/dev/null")
  if not f then return out end
  for line in f:lines() do
    out[#out+1] = line
  end
  f:close()
  return out
end

function mymodule.dir(path)
  local out = {}
  local f = io.popen("ls -1a " .. path .. " 2>/dev/null")
  if not f then return out end
  for line in f:lines() do
    out[#out+1] = line
  end
  f:close()
  return out
end

-- luaposix posix.files(path) returns an iterator over directory entries.
function mymodule.files(path)
  local entries = mymodule.dir(path)
  local i = 0
  return function()
    i = i + 1
    return entries[i]
  end
end

function mymodule.mkdir(path)
  return os.execute("mkdir -p " .. tostring(path))
end

function mymodule.chown(path, uid, gid)
  -- Best-effort for harness; chown often needs root and is unused by tests.
  return true
end

function mymodule.getcwd()
  local f = io.popen("pwd")
  if f then
    local cwd = f:read("*l")
    f:close()
    if cwd and cwd ~= "" then return cwd end
  end
  return "."
end

function mymodule.readlink(path)
  local f = io.popen("readlink " .. tostring(path) .. " 2>/dev/null")
  if not f then return nil end
  local target = f:read("*l")
  f:close()
  return target
end

-- stat(): return a table keyed by stat field names. Best-effort mtime/ctime
-- via ls --time-style when available; fall back to current time.
function mymodule.stat(path, field)
  local st = {}
  local f = io.popen("ls -ld --time-style=+%s " .. path .. " 2>/dev/null")
  if f then
    local line = f:read("*l")
    f:close()
    if line then
      local ts = string.match(line, "%s(%d+)%s")
      if ts then
        local t = tonumber(ts)
        st.mtime = t; st.atime = t; st.ctime = t
      end
    end
  end
  st.mtime = st.mtime or 0
  st.atime = st.atime or 0
  st.ctime = st.ctime or 0
  st.type = "regular"
  if field then return st[field] end
  return st
end

function mymodule.sleep(n)
  if n and n > 0 then
    if n < 1 then
      local t0 = os.time()
      while os.time() - t0 < 1 do end
    else
      os.execute("sleep " .. tostring(n))
    end
  end
end

function mymodule.chmod(path, mode)
  return os.execute("chmod " .. tostring(mode) .. " " .. path)
end

-- crypt(): best-effort; real crypt needs a C module. Used only by
-- authenticator-plaintext for password hashing (not exercised in the
-- default verification path).
function mymodule.crypt(plain, salt)
  return plain
end

return mymodule
