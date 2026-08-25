# abiword-plugin-gdict 3.0.8 Path B candidate evidence

## Application scope

- Task: `contrib-629`
- Task branch: `feat/abiword-plugin-gdict-3.0.8`
- Application path: Path A (base adaptation) + Path B (knowledge extension)
- Candidate draft: `knowledge/drafts/E337-draft-abiword-plugin-host-abi-module.{kv,md}`
- Path B result: subject to reviewer approval

The Path B claim is based on a reusable packaging rule for plugins loaded by a
host application's private ABI. It is not based on patch size, elapsed time,
or the number of build attempts.

## Reusable problem

The gdict source is a plugin inside the complete AbiWord 3.0.8 tree. Building
the whole application would pull a GUI application and its host ABI into a
package whose deliverable is only `gdict.so`. Building only the plugin exposes
the opposite problem: upstream Libtool uses `-no-undefined` and links
`${PLUGIN_LIBS}`, assuming the in-tree AbiWord host library is available.

That assumption is invalid for a standalone plugin package. AbiWord supplies
its host symbols when it loads the module, so forcing a fully resolved link or
inventing a Conan requirement for the unpublished host library changes the
runtime contract rather than adapting it.

## Scoped resolution

For OHOS only, the recipe:

1. builds `plugins/gdict` instead of the full AbiWord application;
2. removes Libtool's `-no-undefined` policy from this module target;
3. omits the unavailable in-tree `${PLUGIN_LIBS}` host linkage;
4. preserves the standard plugin entry points in the packaged shared object;
5. declares the AbiWord 3.0.8 host ABI as a runtime contract, not a Conan build
   requirement.

The package does not add host stubs, copy AbiWord private libraries, suppress
compiler diagnostics, or mix an AbiWord application adaptation into this PR.

## Before/after evidence

| State | Host contract | Result |
|---|---|---|
| upstream module rules | require fully resolved link and in-tree host library | incompatible with a plugin-only package |
| OHOS plugin-only rules | allow host imports to resolve at load time | `gdict.so` built and packaged |
| Shadow r20 | verify artifact and public plugin entry points | 5 passed, 0 failed; runner `rc=0` |

Shadow r20 package reference:

```text
abiword-plugin-gdict/3.0.8#4b38fa7fa081ded08358c23bc5e8870b:245617bc1bd66d4b772e9e617b0ba93fc2d093a5#bddbd8c63b16a74061a1c99e02a46eb1
```

The updated smoke test verifies that the package contains an ELF `DYN` module
and that its dynamic symbol table exports `abi_plugin_register`,
`abi_plugin_unregister`, and `abi_plugin_supports_version`.

## Duplicate boundary

- This is not ordinary transitive dependency propagation: the missing symbols
  belong to the host application that loads the module.
- This is not a missing-library workaround: adding a stub or unrelated shared
  library would hide the required host ABI contract.
- This is not a generic permission repair: the contract applies even on a
  filesystem where every generated file is executable.
- This does not justify unresolved symbols in normal Conan consumer libraries;
  it applies only to an identified host-loaded module with stable entry points.

## Honest validation boundary

The package test proves the module format and exported plugin ABI entry points.
It does not start a complete AbiWord process, exercise host ABI compatibility,
or launch `gnome-dictionary`. Those remain application-integration checks.

## Change boundary

This task changes only `archives/a/abiword-plugin-gdict/3.0.8/` and the directly
related `knowledge/drafts/E337-draft-abiword-plugin-host-abi-module.{kv,md}`.
It does not modify dependency recipes or repository infrastructure.
