# Teal 0.24.5 Compilation Notes

## Build Environment

- Platform: HongMeng (OpenHarmony)
- Lua: LuaJIT 2.1.ROLLING
- Build system: Pure Lua (no configure/make)

## Build Process

### Step 1: Download Source

Source downloaded from GitHub using Python urllib (SSL verification disabled due to platform limitations).

### Step 2: Self-build Test

Teal is self-hosting (written in Teal). The build process:
1. Use existing tl.lua to compile tl.tl
2. Compare generated code with original
3. Self-build test PASSED

### Step 3: Dependencies

- argparse module required for tl CLI tool
- Installed manually by downloading from GitHub

## Issues Encountered

1. SSL certificate verification failed on all HTTPS connections (platform limitation)
   - Solution: Used Python urllib with SSL verification disabled

2. LuaRocks tmpname() failed (E002 /tmp read-only issue)
   - Solution: Downloaded argparse.lua manually

3. argparse master branch version incompatible with tl
   - Solution: Used tl.lua API directly for self-build

4. Lua binary has readline library issues
   - Solution: Used LuaJIT instead

## Self-build Verification

```lua
local tl = require('tl')
local env = tl.init_env(false)
local result = tl.check_file('tl.tl', env)
local lua_code = tl.generate(result.ast, "5.1")
-- Generated code matches original tl.lua
```

Result: PASSED (427724 bytes, identical to original)

## Knowledge Gained

- L2: Teal is self-hosting, requires LuaJIT or Lua 5.1+ for compilation
- L2: argparse CLI dependency can be bypassed by using tl.lua API directly
- L1: HongMeng SSL certificate issues require workaround for HTTPS downloads