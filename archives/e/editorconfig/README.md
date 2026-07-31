# EditorConfig Core C

EditorConfig Core C provides the reference C parser library and the
`editorconfig` command-line tool used to resolve coding-style properties for a
file.

## HarmonyOS PC adaptation

- Builds `libeditorconfig.so.0` and the `editorconfig` CLI with upstream CMake.
- Uses the published `pcre2/10.45` Conan dependency.
- Fetches the exact test repository commit pinned by the upstream v0.12.9 tag.
- Packages relocatable pkg-config metadata and an origin-relative CLI RUNPATH.
- Removes the unneeded static archive from the final package.

## Verification

The Conan consumer reads the library version, creates and parses a real
`.editorconfig` file, and validates the returned `indent_style` and
`indent_size` properties. Cross builds compile and link the consumer but do
not claim runtime execution without a compatible HarmonyOS target.

## References

- https://editorconfig.org/
- https://github.com/editorconfig/editorconfig-core-c
- https://github.com/editorconfig/editorconfig-core-test
