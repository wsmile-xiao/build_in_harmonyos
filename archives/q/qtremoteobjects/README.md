# Qt Remote Objects

Qt Remote Objects provides Qt APIs for sharing object interfaces and state
between processes.

## HarmonyOS adaptation

The Conan recipe uses the `harmonyos-clang` Qt mkspec, builds the core Remote
Objects module, enables the focused upstream POD tests, and generates the
runtime environment required by Qt shared libraries.

## Dependencies

- `qtbase/6.11.1`

## References

- https://doc.qt.io/qt-6/qtremoteobjects-index.html
- https://code.qt.io/cgit/qt/qtremoteobjects.git/
