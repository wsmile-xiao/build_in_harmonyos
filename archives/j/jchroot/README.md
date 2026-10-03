# jchroot

jchroot runs a command inside a chroot that is isolated with Linux namespaces: it
creates new mount/PID/IPC/UTS namespaces (optionally user and network ones),
makes the target a mount point and switches the root with `pivot_root`. The `1.1`
recipe builds the single-binary upstream Makefile target and has no Conan package
requirements; it uses the OpenHarmony system C/POSIX interfaces and packages the
`jchroot` executable, its `jchroot.8` manual page and the ISC license.

The upstream Makefile has no `install` target, so the recipe installs the
artifacts directly instead of running `make install`.
