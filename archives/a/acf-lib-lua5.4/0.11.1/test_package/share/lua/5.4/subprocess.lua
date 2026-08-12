-- subprocess.lua — minimal Lua 5.4 stub for the `subprocess` module acf-lib's
-- apk / db / processinfo modules require() at load time. Test-harness only;
-- not shipped with acf-lib-lua5.4. Provides just enough surface for the
-- pure-Lua code paths of the acf modules to execute under the test runner.
return {
  -- apk / db call this but the pure-Lua paths under test do not invoke it
  call_capture = function() return 0, "stub: no subprocess" end,
  STDOUT = 1,
}
