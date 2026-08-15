# W0 dependency report

- Issue: #2117
- Package: `luaposix/36.3.1.1`
- Checked: 2026-08-13
- Required host dependency: `lua/5.4.8`
- Required build tool: `lua/5.5.0`
- Official remote: `https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`
- Lua 5.4 recipe revision: `0780497a27ff34ad52a2d542b7053eec`
- Lua 5.5 recipe revision: `b376f0ee48d296b7b83296c6b4c4b529`
- Result: pass

`luaposix/36.3` and `luaposix/36.3.1` are already published for Lua 5.5. The
latter has remote recipe revision `38ed11f234935205f489d427c8102449` and
cannot be replaced because the registry does not support a second recipe under
the same version. The remote has no `luaposix/36.3.1.1`, so this next adaptation
revision preserves both existing contracts while providing the Lua 5.4 ABI
required by the ACF dependency graph.

The Lua 5.4 package provides the target headers and static library but no
interpreter. The Lua 5.5 package provides `bin/lua` for the build-context
`luke` script. It does not contribute headers or libraries to the package
artifacts.
