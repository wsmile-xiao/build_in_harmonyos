# xcb-proto 1.17.0 W0 dependency report

## Result

The `xcb-proto/1.17.0` artifact is not published in the `ohpcd` Conan remote,
so dependency Issue #1310 was created for this prerequisite. The recipe itself
has no third-party Conan requirements and can proceed without another split
dependency.

## Artifact evidence

Checks used a new Conan home and did not use `--build=missing`:

```text
conan download xcb-proto/1.17.0 -r=ohpcd --only-recipe
exit 1: remote acceleration-policy error

conan install --requires=xcb-proto/1.17.0 -r=ohpcd --build=never
exit 1: Unable to find 'xcb-proto/1.17.0' in remotes
```

The second command reached package resolution and is the decisive absence
evidence. A same-name Issue search was read back after creation and returns
only open dependency Issue #1310.

## Dependency evidence

- Upstream `configure.ac` declares Python and optional `xmllint` as tools.
- `src/Makefile.am` installs XML/XSD data; `xcbgen/Makefile.am` installs Python
  source. Neither declares a third-party runtime library.
- The Conan recipe defines no `requirements()`, `build_requirements()`, or
  `tool_requirements()` method and exports no linked libraries.
- libxcb consumes `xcb-proto.pc`, the protocol XML, and `xcbgen` during code
  generation. This makes xcb-proto a real build/data prerequisite, not a
  runtime link dependency.

The package is outside the contest task list, so policy requires only the
dependency Issue and not a second contest-claim Issue.
