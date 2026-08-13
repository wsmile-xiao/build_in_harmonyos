# E319 draft - Bundled Waf 2.0.x fails after Python removes `imp`

> Status: DRAFT | Source: JACK 1.9.22 PR #3482, commit `98d26a683`

## Error signature

An archive contains an older Waf copy and invokes it with Python 3.12 or
newer. Configuration stops in `waflib/Context.py` because the loader imports
the removed `imp` module or calls `imp.new_module()`.

```text
ModuleNotFoundError: No module named 'imp'
```

## Root cause

Waf 2.0.12 creates the module used for a `wscript` with
`imp.new_module(WSCRIPT_FILE)`. Python 3.12 removed `imp`; the equivalent
standard-library API is `types.ModuleType`.

This is a build-system compatibility issue, not a compiler or OHOS libc
failure. It can occur for any package that vendors the affected Waf version.

## Minimal repair

Patch the vendored loader only:

```python
# waflib/Context.py
from types import ModuleType

# Previous: module = imp.new_module(WSCRIPT_FILE)
module = ModuleType(WSCRIPT_FILE)
```

Then validate both the patch applicability and Python syntax:

```bash
git apply --check 0004-waflib-Context.py.patch
python3 -m py_compile waflib/Context.py
```

Do not substitute a different system Waf release without separately proving
that its configure, build, and install behavior matches the package's bundled
version.

## Evidence

JACK 1.9.22 carries `0004-waflib-Context.py.patch`, which changes only the
import and module-construction call in Waf 2.0.12. The patched module passes
`py_compile`; the recipe retains the upstream bundled Waf and invokes it with
`python3 ./waf`.
