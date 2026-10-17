-- posix.lua — minimal Lua 5.4 stub for the `posix` module acf-lib's fs /
-- date / processinfo modules require() at load time. Test-harness only;
-- not shipped with acf-lib-lua5.4. Provides just enough surface for the
-- pure-Lua code paths of the acf modules to execute under the test runner.
return {
  -- fs / date read these but the pure-Lua paths under test do not invoke them
  getenv = function(name) return os.getenv(name) end,
  stat = function() return nil, "stub: no fs" end,
  time = function() return os.time() end,
  uname = function() return { sysname = "OHOS" } end,
}
