# E337 - Preserve the host ABI contract for an independently packaged plugin

> Contributor: xuguowei | Status: DRAFT | Created: 2026-08-24

## Scope

Use this pattern when an ELF plugin is built from a larger application tree,
the host application is not a separately published build dependency, and the
host process is expected to resolve private ABI imports when loading the
module.

This pattern does not apply to normal shared libraries, plugins with a complete
public SDK/import library, or executables that must have all symbols resolved
at link time.

## Symptom

Building the full upstream project is out of scope because it produces an
application rather than the requested plugin package. Building only the plugin
then fails because upstream rules use `-no-undefined` and link an in-tree host
library that the standalone recipe deliberately does not build.

Adding unrelated libraries does not solve the problem. The missing contract is
the host application ABI supplied by the process that loads the plugin.

## Root cause

The upstream build assumes the plugin and host are built together. Its link
policy is correct in that context but is not a complete packaging model for an
independent module. Treating the host ABI as an ordinary Conan build
requirement is also incorrect when no stable host SDK package exists.

For AbiWord gdict 3.0.8, the module exposes three loader entry points while
other AbiWord symbols are provided by the AbiWord process at load time:

```text
abi_plugin_register
abi_plugin_unregister
abi_plugin_supports_version
```

## Recommended solution

1. Confirm that the artifact is a host-loaded module rather than a normal
   consumer library.
2. Identify the host version and loader entry points that define the contract.
3. Build only the plugin target.
4. Remove the fully-resolved-link policy only from that module target.
5. Omit unavailable in-tree host linkage; do not add stubs.
6. Package the module and validate its ELF type and exported entry points.
7. Keep full host loading as a separate application-integration test.

For gdict the package smoke test uses `readelf` to require an ELF `DYN` object
and all three entry points above.

## Before/after evidence

| State | Result |
|---|---|
| upstream plugin rules plus plugin-only build | requires the unavailable in-tree host link and fully resolved symbols |
| scoped OHOS module rules | builds and packages `gdict.so` while retaining the loader contract |
| Shadow r20 | Conan create and 5 artifact/ABI checks passed; runner returned `rc=0` |

## Forbidden shortcuts

- Do not link a fake or stub host implementation merely to satisfy the linker.
- Do not disable undefined-symbol checks globally for every project target.
- Do not claim runtime compatibility from symbol-table inspection alone.
- Do not mix a full host application adaptation into the plugin package.

## Validation boundary

ELF and exported-symbol checks prove that the package contains a loadable module
shape and the expected loader entry points. They do not prove that a complete
host can load the plugin, that every private ABI import matches, or that the
external dictionary application launches. Final Path B recognition remains a
reviewer decision.
