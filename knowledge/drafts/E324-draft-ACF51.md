# E324 draft: Pure Lua 5.1 module packaging on HarmonyOS PC

## Purpose

This draft records a reusable Conan pattern for pure Lua 5.1 packages. Such
packages do not compile their own native code, but they are not ordinary data
archives: their install layout, `LUA_PATH`, interpreter version, and runtime
`require` behavior form the consumer contract.

The source event is `acf-lib-lua5.1/0.11.1` in issue #2140 and PR #5253.

## Failure model

A package can contain every upstream `.lua` file and still fail on the target:

1. Lua 5.1 searches versioned module roots such as `share/lua/5.1`.
2. Upstream may install canonical modules below a namespace while exposing
   legacy top-level names through symbolic links.
3. HMDFS may not resolve those links, so `require("acf.format")` can work while
   the promised `require("format")` compatibility entry fails.
4. A host Lua interpreter does not prove that the target's Conan-provided Lua
   5.1 can parse, load, and execute the packaged code.
5. Modules with optional integrations can fail during `require` before their
   dependency-independent behavior is reached.

## Recommended recipe pattern

### 1. Fix the source contract

- Pin the release URL and SHA-256.
- Maintain the exact expected module inventory.
- Reject unexpected, missing, or empty modules before packaging.
- Declare all four target profile settings: `os`, `compiler`, `build_type`, and `arch`.
- Declare the matching interpreter dependency, such as `lua/5.1`.

### 2. Preserve import compatibility without symlinks

Install canonical and promised compatibility entries as real copies. For an
upstream layout that installs `acf/*.lua` and links top-level names, package:

```text
share/lua/5.1/acf/format.lua  # require("acf.format")
share/lua/5.1/format.lua      # require("format")
```

Do not create aliases that upstream does not advertise. If upstream only
documents the namespace, package and test only that namespace.

### 3. Publish the interpreter search path

Expose the versioned roots through both Conan build and run environments. Keep
Lua's default search path by ending the value with `;;`:

```python
lua_path = ";".join((
    os.path.join(lua_root, "?.lua"),
    os.path.join(lua_root, "?", "init.lua"),
    os.path.join(lua_root, "acf", "?.lua"),
))
self.buildenv_info.define("LUA_PATH", lua_path + ";;")
self.runenv_info.define("LUA_PATH", lua_path + ";;")
```

The OHOS CI profile gate requires the complete settings declaration even for a
source-only package:

```python
settings = "os", "compiler", "build_type", "arch"

def package_id(self):
    self.info.clear()
```

Clearing the package ID keeps one reusable source artifact while the recipe
graph still declares the exact interpreter-version requirement.

### 4. Execute a target consumer

The `test_package` must use the target Lua dependency, not whichever `lua`
happens to be installed on the build host. A small C runner linked to
`lua/5.1` is sufficient when the dependency package does not ship a CLI.

The consumer should verify:

- every installed canonical and compatibility entry;
- every documented `require` name;
- representative successful behavior;
- representative error behavior;
- a machine-readable result marker for CI discovery.

### 5. Isolate optional-dependency stubs

When compatible OHOS packages for optional integrations are not yet available,
minimal stubs may be placed under `test_package` to drive dependency-independent
paths. They must never enter the package, and the test must load the real module
from the package folder before the stub paths. This is validation scaffolding,
not a substitute for separately adapting required dependencies.

## Evidence from acf-lib-lua5.1

- Eight upstream modules are checked against an exact inventory.
- Sixteen real files preserve eight namespaced and eight compatibility imports.
- Eight namespaced imports and one compatibility import are executed.
- Format and validator behavior cover successful and failing inputs.
- Ten real `acf.db` runtime assertion sites are driven with test-only LuaSQL,
  POSIX, and subprocess stubs.
- The target runner links the separately adapted `lua/5.1` Conan package.
- Shadow CI build #24739 passed Conan `test_package`, L0, and L1. The two
  fail-closed Lua scripts executed and passed all 45/45 checks.

## Boundary with existing knowledge

- E050 explains the general HMDFS symbolic-link failure and copy replacement;
  it does not define Lua module roots, import compatibility, or target `require`
  validation.
- E132 explains the OHOS SDK `lld` runtime library path; it is only needed while
  linking the target runner.
- E216 covers building the native `lua/5.1` C library without Make/CMake; this
  draft covers downstream pure Lua source-module packages.
- E241 covers architecture-neutral data/rule packages; pure Lua modules add an
  interpreter ABI/version and executable runtime contract.

## Non-goals

- Lua C extension modules, which require native ABI and shared-library handling.
- Claiming optional integrations work without separately adapted dependencies.
- Replacing upstream behavior or weakening target-side assertions.

This is a Path B knowledge-extension candidate with package-level evidence from
shadow CI #24739. Final classification remains subject to project review.
