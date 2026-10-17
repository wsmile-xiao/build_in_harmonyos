# xorgproto 2025.1 W0 dependency report

## Result

W0 passed. The recipe has no third-party Conan runtime, build, or tool
requirements, so there is no unpublished Conan dependency to split out before
xorgproto 2025.1.

## Evidence

- `conanfile.py` defines no `requirements()`, `build_requirements()`, or
  `tool_requirements()` method.
- The official source is architecture-independent protocol data: public C
  headers, pkg-config templates, licenses, and protocol documents.
- Python executes the upstream optional keysym verification during the recipe
  build. Clang compiles the test consumers. Both are tools supplied by the
  build/test environment, not libraries exported to downstream consumers.
- `package_info()` exports only the package include directory and pkg-config
  search path; it exports no linked libraries or transitive requirements.

The repository preflight script was run from its LF Git blob against this
worktree's `archives` directory:

```bash
ARCHIVES_ROOT=<current-worktree>/archives \
  bash ci/scripts/preflight_check.sh xorgproto/2025.1
```

It returned 0 with `preflight passed (no dependencies to check)`. The LF blob
was used because the Windows checkout has CRLF line endings that WSL Bash
rejects before argument processing; no repository script was modified.

## Downstream order

xorgproto is a real X11/AWT prerequisite for the current OpenJ9 and GraalVM
adaptations. Those downstream recipes must continue to wait until this
dependency PR is merged and `xorgproto/2025.1` is published.
