# xmlm

Streaming XML codec for OCaml: decode and encode the XML data format without
building a complete in-memory representation of the document. Ships the
`xmlm` OCaml library and the `xmltrip` command-line inspection tool.

## Homepage

https://erratique.ch/software/xmlm

## License

ISC

## Versions

| Version | Status |
|---------|--------|
| 1.4.0 | built |

## Build notes

Built with the registry OCaml toolchain (`ocaml/4.14.1.1.4`). Upstream uses
topkg + ocamlbuild; neither is available in the registry, so the recipe
compiles the unmodified sources directly with `ocamlc`/`ocamlopt`. Requires an
`as` shim forwarding to the OHOS clang, `-cc <clang>` on all `ocamlopt`
invocations, and `-ccopt -shared` for the `.cmxs` link. See
`1.4.0/notes.md` for details.
