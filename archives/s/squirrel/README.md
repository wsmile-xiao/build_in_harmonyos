# Squirrel

Squirrel is a lightweight embeddable scripting language VM and standard library.
The OpenHarmony PC recipe currently provides the static `squirrel` and `sqstdlib`
libraries plus the `sq_static` command for `armv8` targets.

The versioned recipe and consumer test are under `3.2/`. The consumer exercises
the public VM lifecycle (`sq_open`, root-table push/pop, and `sq_close`) so a
successful package test proves that the installed headers and libraries are
actually linked.
