# E331 - Task-local recursive Libtool metadata closure

> Contributor: 2301_80739235 | Status: DRAFT | Created: 2026-08-19

## Scope

Use this pattern when an Autotools project consumes a shared Conan dependency
through Libtool and published `.la` files retain paths from an older Conan
home. E236 remains the preferred solution for static-only dependencies that can
use a private `.la`-free archive directory. This draft covers the different
case where Libtool metadata and shared library names must remain available.

## Symptom

The direct dependency appears repaired, configure succeeds, and all objects
compile. The final Libtool link then fails on a transitive archive:

```text
libtool: warning: library '.../libxcb.la' was moved
libtool: error: '.../.conan2/.../libXau.la' is not a valid libtool archive
```

Windows graph-only generation can expose related host/target failures first:

```text
PatternError: bad escape \H at position 10
cannot uniquely rebind : found 0
```

The second message can come from target token `//lib/libxcb.la`: Windows
`Path` treats it as a UNC anchor and returns an empty basename.

## Root cause

Libtool recursively reads every `.la` named in `dependency_libs`. Rewriting
only `libX11.la` still leaves paths embedded in `libxcb.la`, `libXau.la`, or
later graph nodes. Search order also matters: if an original dependency
directory precedes the shadow directory, `-lX11` resolves to the original
metadata before the repaired copy.

Cross-host generation has separate path grammars. Regex replacement strings
interpret Windows backslashes, while target paths beginning with `/` or `//`
must be parsed with POSIX semantics even when generation runs on Windows.

## Recommended solution

1. Enumerate dependency `.la` files and reject ambiguous basenames.
2. Create a directory below the current build folder; never edit dependency
   package directories.
3. Copy each archive's declared `library_names` and `old_library` files into
   that directory.
4. Rewrite every `.la` token in the complete `dependency_libs` closure to the
   corresponding shadow archive.
5. Rewrite dependency cache `-L` tokens to one shadow `-L`, bind every shadow
   `libdir` to the shadow, and put it before original dependency libdirs.
6. Use callable `re.subn` replacements for path-bearing values. Use
   `PurePosixPath(token).name` for target tokens that begin with `/`.
7. Fail closed on a missing artifact, ambiguous basename, stale cache token,
   or shadow-external `.la` reference.

## Verification

For libxfixes 6.0.2, fresh isolated W0 r14 produced 29 shadow `.la` files and
87 declared library files, with zero stale cache tokens and zero external `.la`
references. Exact-snapshot W3 r5 then passed:

- static `conan create` and both package consumers;
- shared `conan create` and both package consumers;
- upstream `make check` in both option builds (truthful inventory 0/0);
- official finish and exact `.ci-result.json` readback.

The W3 input tree was `0183a789e5851f9e3ddf13bf0dd29644bf350e3b`.
Dependency package caches were not modified.

## Forbidden shortcuts

- Do not rewrite or delete `.la` files in a Conan package cache.
- Do not repair only the first archive in a transitive Libtool chain.
- Do not use host `Path` semantics for target `//lib/...` tokens.
- Do not put the original dependency directories before the shadow.
- Do not replace a shared dependency with an absolute `.a` without the E236
  nested-archive checks.
