# Draft: libfirm 1.22.0 — Python 3.12 compatibility for vendored build generators

> Source event: `libfirm/1.22.0` HarmonyOS PC (aarch64-linux-ohos) adaptation, executor pc2-39.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

The bundled build-time code generators crash on Python 3.12 before any C file
is compiled:

```text
ModuleNotFoundError: No module named 'imp'                          (gen_ir.py, irops.py)
ImportError: cannot import name 'Mapping' from 'collections'        (markupsafe/__init__.py, jinja2/tests.py)
re.error: global flags not at the start of the expression           (jinja2/filters.py _word_re = re.compile(r'\w+(?u)'))
```

## Root cause

- `imp` was removed in Python 3.12 (use `importlib.util`).
- `collections.Mapping`/`MutableMapping` moved to `collections.abc` (Python 3.10+).
- Inline regex flags like `(?u)` are rejected unless at the start (Python 3.11+).
- libfirm ships jinja2 2.8-dev / markupsafe from 2015 (all of the above).

## Recommended fix (minimal in-tree patches, captured by refresh-patch --auto)

1. `gen_ir.py`: `import imp` → `import importlib.util`; `imp.load_source('spec', f)` →
   `spec_from_file_location` + `exec_module`.
2. `irops.py`: drop the unused `import imp`.
3. `markupsafe/__init__.py`, `jinja2/tests.py`: `from collections import Mapping` →
   `try: from collections.abc import Mapping except ImportError: from collections import Mapping`.
4. `jinja2/filters.py`: `_word_re = re.compile(r'\w+(?u)')` → `re.compile(r'\w+', re.UNICODE)`.

Also ensure `python` resolves (the generators use `#!/usr/bin/env python`):
add a `python -> python3` link dir on `PATH` in the recipe `generate()`.

## Evidence from libfirm

| Fix | Result |
|-----|--------|
| before | `imp` / `Mapping` / regex crashes; `build/gen/include/libfirm/nodes.h` empty |
| after | nodes.h regenerated (4316 lines), `make` exit 0, `conan create` G1-G4 pass |

## Applicability boundary

- Python-2-era vendored helpers inside a C project's build scripts, built with
  host Python >= 3.10.
- The recipe must not depend on pip-provided replacements (vendored copy wins on
  sys.path; CI is clean).

## Counter-examples / limits

- Modern jinja2 (3.x) does not need these fixes.
- If the crash is outside vendored helpers (e.g. top-level project script), the
  same importlib/collections.abc recipe still applies.
- `python` missing from PATH is a separate, environment-level issue; the symlink
  only fixes script resolution, not the language incompatibilities above.

## Related knowledge

- similar_to: E339 (imp removed, waf generator)