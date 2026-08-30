# DRAFT: eigenpy jrl-cmakemodules source fallback

> Status: Draft | Updated: 2026-08-29
> Source event: `eigenpy/3.13.0` HarmonyOS PC adaptation

## Summary

The `eigenpy` 3.13.0 PyPI sdist carries `.gitmodules`, but it does not include
the `cmake/` `jrl-cmakemodules` submodule content required by configure. A Conan
recipe should fetch that exact submodule commit during `source()` instead of
letting upstream CMake run `FetchContent` during `build()`.

For this version, upstream `v3.13.0` points `cmake/` to commit
`f07de7952b35caf1c7a53a49138772cb9c534cf5`.

## Symptoms

- `cmake/base.cmake` is missing after unpacking the PyPI sdist.
- Configure logs say `JRL cmakemodules not found. Let's fetch it.`
- CI reaches configure/build and then depends on live GitHub access.
- Direct GitHub codeload for the submodule is slow or times out.

## Adaptation Pattern

Add a second `conandata.yml` entry for the submodule archive and unpack it into
`${source_folder}/cmake`:

```python
get(self, **self.conan_data["sources"], strip_root=True)
get(
    self,
    **self.conan_data["cmake_submodule"],
    destination=os.path.join(self.source_folder, "cmake"),
    strip_root=True,
)
```

Keep the SHA256 fixed. If a mirror is needed, use a URL list and verify that the
mirror archive matches the same SHA256 as the direct GitHub archive.

## Validation

Run a source-only check outside the archive directory:

```sh
conan source <recipe-copy> --name=eigenpy --version=3.13.0
test -f cmake/base.cmake
test -f CMakeLists.txt
test -f unittest/CMakeLists.txt
```

In the 2026-08-29 precheck, direct GitHub codeload timed out after 60 seconds at
about 1.2 MB, while the gh-proxy GitHub archive completed in about 10 seconds and
matched the pinned SHA256.

## Do Not

- Do not let CMake `FetchContent` download `jrl-cmakemodules` during `build()`.
- Do not vendor the unpacked submodule source into `archives/e/eigenpy/3.13.0`.
- Do not use a mirror without preserving the pinned SHA256 check.
