# kamilalisp

[KamilaLisp](https://github.com/iczelia/kamilalisp) ("Two: Electric Boogaloo")
is a functional, flexible and concise Lisp interpreter influenced by Haskell and
APL. It is implemented in **Java 17** and built with **Maven**; the release
artifact is a runnable fat JAR (`kamilalisp-0.3.jar`, `Main-Class:
palaiologos.kamilalisp.repl.Main`).

This package adapts KamilaLisp for **HarmonyOS PC (aarch64)** and exposes the
`kamilalisp` CLI (REPL / script interpreter) via the package `bin/`.

## Versions

| Version | Status |
| --- | --- |
| 0.3.0.1 | built |

Homepage: https://github.com/iczelia/kamilalisp

## Usage

```sh
conan install --requires=kamilalisp/0.3.0.1
kamilalisp              # interactive REPL
kamilalisp prog.lisp    # run a KamilaLisp script
```

Runtime requires BiSheng JDK 17 (`java` on PATH or `JAVA_HOME`).
