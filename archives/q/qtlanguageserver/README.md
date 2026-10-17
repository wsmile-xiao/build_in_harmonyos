# Qt Language Server

Qt Language Server provides Qt's private JSON-RPC and Language Server
Protocol libraries.

## HarmonyOS adaptation

The Conan recipe configures Qt with the `harmonyos-clang` mkspec, enables and
executes the upstream tests, and disables examples, benchmarks, and manual
tests. The package exports the static `Qt6LanguageServerPrivate` and
`Qt6JsonRpcPrivate` libraries.

## Dependencies

- `qtbase/6.11.1`

## References

- https://doc.qt.io/qt-6/qtlanguageserver-index.html
- https://code.qt.io/cgit/qt/qtlanguageserver.git/
