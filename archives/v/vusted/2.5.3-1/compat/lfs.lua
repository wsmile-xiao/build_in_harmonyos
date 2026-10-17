local uv = assert(vim and (vim.uv or vim.loop), "vusted lfs compatibility requires Neovim vim.uv")

local lfs = {
  _VERSION = "LuaFileSystem 1.8.0 vusted compatibility",
}

local function time_value(value)
  if type(value) == "table" then
    return (value.sec or 0) + (value.nsec or 0) / 1000000000
  end
  return tonumber(value) or 0
end

local function stat_table(path, stat_fn)
  local stat, err = stat_fn(path)
  if not stat then
    return nil, err or "cannot stat path", 2
  end
  return {
    mode = stat.type,
    size = stat.size or 0,
    access = time_value(stat.atime),
    modification = time_value(stat.mtime),
    change = time_value(stat.ctime),
  }
end

function lfs.attributes(path, key)
  local attrs, err, code = stat_table(path, uv.fs_stat)
  if not attrs then
    return nil, err, code
  end
  if key then
    return attrs[key]
  end
  return attrs
end

function lfs.symlinkattributes(path, key)
  local stat_fn = uv.fs_lstat or uv.fs_stat
  local attrs, err, code = stat_table(path, stat_fn)
  if not attrs then
    return nil, err, code
  end
  if key then
    return attrs[key]
  end
  return attrs
end

function lfs.currentdir()
  if vim and vim.fn and vim.fn.getcwd then
    return vim.fn.getcwd()
  end
  return assert(uv.cwd())
end

function lfs.chdir(path)
  if vim and vim.cmd and vim.fn and vim.fn.fnameescape then
    local ok, err = pcall(vim.cmd, "cd " .. vim.fn.fnameescape(path))
    if ok then
      return true
    end
    return nil, err
  end
  if uv.chdir then
    local ok, result, err = pcall(uv.chdir, path)
    if not ok then
      return nil, result
    end
    if result == nil and err then
      return nil, err
    end
    return true
  end
  return nil, "changing directory is not supported by this Neovim runtime"
end

function lfs.mkdir(path)
  local ok, err = uv.fs_mkdir(path, 493)
  if ok then
    return true
  end
  return nil, err
end

function lfs.rmdir(path)
  local ok, err = uv.fs_rmdir(path)
  if ok then
    return true
  end
  return nil, err
end

local function scandir_entry(entry, entry_type)
  if type(entry) == "table" then
    return entry.name or entry[1], entry.type or entry[2]
  end
  return entry, entry_type
end

function lfs.dir(path)
  local scan, err = uv.fs_scandir(path)
  if not scan then
    return nil, err or ("cannot open directory: " .. tostring(path))
  end
  if type(scan) == "table" then
    if scan.name or scan.type then
      local done = false
      return function()
        if done then
          return nil
        end
        done = true
        return scandir_entry(scan)
      end
    end
    local index = 0
    return function()
      index = index + 1
      return scandir_entry(scan[index])
    end
  end
  return function()
    local name, entry_type = uv.fs_scandir_next(scan)
    return scandir_entry(name, entry_type)
  end
end

return lfs
