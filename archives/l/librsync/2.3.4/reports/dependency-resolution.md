# librsync 2.3.4 dependency resolution

## popt/1.16

`librsync` enables `BUILD_RDIFF=ON`, so the recipe requires `popt/1.16`.
Although the source tree still contains an old partial archive under
`archives/p/popt/1.16`, this package consumes the published Conan recipe from
the `ohpcd` remote.

Verified on 2026-08-04 with the workspace Conan cache:

```text
conan download "popt/1.16" -r=ohpcd --only-recipe

Local Cache
  popt
    popt/1.16
      revisions
        cca44e0c65c2ff043d329f27a068a956 (2026-08-04 08:19:02 UTC)
Connecting to remote 'ohpcd' anonymously
Skip recipe popt/1.16#cca44e0c65c2ff043d329f27a068a956 download, already in cache
Download completed in 0s
```

The OHOS PC runner verification on port 33332 consumed this dependency and
completed `ci/conan/build_and_test.sh archives/l/librsync/2.3.4` with
`BUILD_RDIFF=ON`: 15 upstream CTest cases passed, including the 8 `rdiff` CLI
tests that require `popt`.

The downloaded remote recipe cache contains both required recipe files:

```text
conandata.yml
conanfile.py
conanmanifest.txt
```

This is the dependency source used by Conan resolution. It is distinct from the
older source-tree archive under `archives/p/popt/1.16`, which remains marked as
partial in the repository.

## perl/5.42.2

`tests/mutate.test` executes a Perl script. The recipe declares
`perl/5.42.2` as a tool requirement so the upstream `Mutate` CTest runs in the
Conan build environment on OHOS.
