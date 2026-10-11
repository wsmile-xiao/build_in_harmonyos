# topkg

The transitory OCaml software packager: an OCaml library that describes the
files a package installs, and drives its build/distribution/publication
procedures. Upstream packages (e.g. xmlm) use it as a build dependency via
`pkg/pkg.ml`.

## Homepage

https://erratique.ch/software/topkg

## License

ISC

## Versions

| Version | Status |
|---------|--------|
| 1.1.1 | built |

## Build notes

Library package (no CLI binary; the `topkg` command lives in the separate
`topkg-care` package). Built with the registry OCaml toolchain
(`ocaml/4.14.1.1.4`). The upstream topkg bootstrap (which needs ocamlfind and
ocamlbuild) is replaced by a direct ocamlc/ocamlopt compilation of the
unmodified sources; `ocamlbuild/0.16.1` is being published as a separate
dependency task. See `1.1.1/notes.md` for details.
