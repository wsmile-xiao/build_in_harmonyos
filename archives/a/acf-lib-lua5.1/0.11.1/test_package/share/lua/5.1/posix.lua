return {
  getenv = function(name) return os.getenv(name) end,
  stat = function() return nil, "test stub: no filesystem" end,
  time = function() return os.time() end,
  uname = function() return {sysname = "OHOS"} end,
}
