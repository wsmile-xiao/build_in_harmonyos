# Legacy Python setup metadata can require Git history missing from codeload archives

> Path B draft grounded in shyaml 0.6.2 and independently checked against vaab/colour 0.1.5.

## Failure signature

A clean codeload source tree contains `setup.py`, `setup.cfg`, and `autogen.sh`, but no `.git`.
When the version placeholders are unexpanded, setup invokes `autogen.sh`; the generator calls
`git describe --tags` and exits because the extracted archive has no repository metadata.

For shyaml 0.6.2, the archive leaves `%%version%%` in both `setup.py` and `shyaml.py`. Its
`setup.py` detects the placeholder and starts `autogen.sh`; that script explicitly requires a
successful `git describe --tags`. The project is still a small pure-Python module, so the
source-history dependency is packaging metadata generation rather than compilation.

## Evidence and a second upstream

The exact shyaml tag is `70d793ae0d2bf84e5d4d0944d0801af1714830a2`. The codeload archive is
23,152 bytes with SHA-256 `72d2b99a5e50ca852c4fe85d21e1b818a29ca6a9430399c3b8c4d8a3d8d6cca5`.
Its `setup.py` fallback checks the placeholder, invokes `autogen.sh`, and its `.package` file
sets the release name and metadata. The archive has no `.git` entry.

An independent tag archive, vaab/colour 0.1.5, contains the same `.package` + `autogen.sh` +
`setup.py` layout. The generated metadata workflow is therefore reusable across more than the
shyaml checkout. It is narrower than generic `git describe` version scripts: it is the Python
setuptools fallback that recursively invokes setup after mutating release metadata files.

## Recommended handling

1. Pin the exact upstream tag archive and SHA-256.
2. Inspect setup.py, setup.cfg, and the generator before choosing pip install. If the archive
   has release placeholders and the generator requires `.git`, do not run the fallback blindly.
3. For a pure single-module package, stage the module directly under
   `lib/pythonX.Y/site-packages`, substitute the verified recipe version, and generate a small
   relocatable console launcher. Keep declared Python modules such as PyYAML as Conan runtime
   dependencies.
4. Run the upstream tests from the source tree. Doctests and executable shell examples are
   separate suites; invoke the project's real test entry point when its runner dependency can be
   supplied. If a required shell is absent, run the independent Python doctests and record the
   shell suite as skipped with the concrete worker limitation.
5. Test the installed launcher from the consumer package so packaging bypasses cannot mask a
   broken entry point or missing runtime dependency.

## Prohibited shortcuts

- Do not replace the tag coordinate with `main` or `master` to make `git describe` succeed.
- Do not leave `%%version%%` in the installed module; `--version` then reports `unreleased`.
- Do not skip the upstream `bin/test` suite merely because `pip install` fails. The package can
  be staged directly while its source tests still run normally.

## Boundary against existing knowledge

`DRAFT-libcork-0.9.0-version-sh-git-describe` covers shell `version.sh` fallback, quoting, and
`/bin/bash` portability. `DRAFT-libfirm-1.22.0-makefile-version-header-tarball` covers a Makefile
version header. This draft covers a distinct Python packaging path: setuptools sees unresolved
metadata tokens, calls a Python-specific autogen fallback, and requires legacy `d2to1`/generated
metadata. E430 concerns archive checksum authority, not release-version generation.
A main-tip search for the implementation-specific signatures
`d2to1`, `%%short-version%%`, and `docshtest` returned zero hits:
`git grep -inE 'd2to1|%%short-version%%|docshtest' origin/main -- knowledge/graph knowledge/doc knowledge/drafts`.
The nearby draft searches show the broader no-`.git` version problem, while this Python fallback
and its shell-doc test runner are absent.

The initial local HarmonyOS run completed 33/33 `shyaml.py` doctests, 4/4 `README.rst` Python
doctests, and 63/63 executed docshtest examples; one LibYAML-only example was conditionally skipped
by the upstream harness. CI then showed that its OHOS worker has no `bash`, which the upstream
`bin/test` shell runner requires. The revised recipe retains the 37 Python doctests and records the
64 shell examples as skipped for that worker limitation; the installed consumer CLI remains checked
after packaging. The revised HarmonyOS `conan create` exited 0 with the 37 doctests and five
consumer checks passing. The adaptation only bypasses setup.py because shyaml is a single
pure-Python module. Packages
with C extensions, custom build backends, package discovery, or complex entry points should first
materialize their exact VCS metadata or use a complete pinned source distribution.

## Evidence files

- Upstream source: `https://github.com/0k/shyaml/tree/0.6.2`
- Independent pattern check: `https://github.com/vaab/colour/tree/0.1.5`
- Recipe and upstream test output: `archives/s/shyaml/0.6.2/`
- HarmonyOS validation: `conan create archives/s/shyaml/0.6.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
