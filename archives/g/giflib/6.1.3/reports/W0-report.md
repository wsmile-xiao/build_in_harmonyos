# giflib 6.1.3 W0 dependency report

## Result

The `giflib/6.1.3` artifact is not published in the `ohpcd` Conan remote.
This library is outside the current contest task list, so policy requires one
dependency Issue and no second contest-claim Issue. The recipe itself has no
third-party Conan requirement and can proceed without another split package.

## Artifact evidence

The target check used a new Conan home and did not use `--build=missing`:

```text
conan download giflib/6.1.3 -r=ohpcd --only-recipe
exit 1: remote acceleration policy not enabled

conan install --requires=giflib/6.1.3 -r=ohpcd --build=never
exit 1: Unable to find 'giflib/6.1.3' in remotes
```

The install command reached package resolution and is the decisive absence
evidence. Its log SHA256 is
`11064bde19a299ab4911f057e57860d60b09e731e54300a7111825d44914f22c`.
A full same-name Issue scan found no `giflib 6.1.3` identity. The open
`giflib 5.2.2` Issue #1107 belongs to an older version and is not modified or
reused.

## Dependency evidence

- The upstream Makefile links giflib only with the C runtime.
- The final shared ELF reports only `libc.so` in its NEEDED entries.
- The Conan recipe has no `requirements()`, `build_requirements()`, or
  `tool_requirements()` method.
- Make, clang, LLVM signing tools, CMake, Python, and Conan are build/test
  tools rather than exported runtime dependencies.

giflib 6.1.3 is submitted as dependency Issue #1315, a real prerequisite of
GraalVM Issue #1085. Issue #1315 links #1085, and #1085 contains the unique
reverse dependency link to #1315.
