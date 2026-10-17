local uv = vim and (vim.uv or vim.loop)

local system = {
  CODEPAGE_UTF8 = 65001,
}

function system.gettime()
  if uv and uv.gettimeofday then
    local sec, usec = uv.gettimeofday()
    if type(sec) == "table" then
      return (sec.sec or 0) + (sec.usec or 0) / 1000000
    end
    if sec then
      return sec + (usec or 0) / 1000000
    end
  end
  return os.time()
end

function system.monotime()
  if uv and uv.hrtime then
    return uv.hrtime() / 1000000000
  end
  if uv and uv.now then
    return uv.now() / 1000
  end
  return os.clock()
end

function system.sleep(delay)
  delay = tonumber(delay) or 0
  if delay <= 0 then
    return true
  end
  if uv and uv.sleep then
    uv.sleep(math.floor(delay * 1000))
    return true
  end
  if vim and vim.wait then
    vim.wait(math.floor(delay * 1000))
    return true
  end
  local target = os.clock() + delay
  while os.clock() < target do
  end
  return true
end

function system.isatty()
  return false
end

function system.termbackup()
  return { __vusted_compat = true }
end

function system.termrestore()
  return true
end

function system.autotermrestore()
  return true
end

function system.termwrap(fn)
  return fn
end

function system.getconsoleflags()
  return nil
end

function system.setconsoleflags()
  return true
end

function system.tcgetattr()
  return nil
end

function system.tcsetattr()
  return true
end

function system.getnonblock()
  return false
end

function system.setnonblock()
  return true
end

function system.getconsoleoutputcp()
  return system.CODEPAGE_UTF8
end

function system.setconsoleoutputcp()
  return true
end

function system.getconsolecp()
  return system.CODEPAGE_UTF8
end

function system.setconsolecp()
  return true
end

return system
