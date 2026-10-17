# wtype

`wtype` is a command-line tool that sends keyboard input through the Wayland virtual-keyboard protocol.

## HarmonyOS PC

The `0.4` Conan recipe builds an AArch64 executable for HarmonyOS PC. Wayland and libxkbcommon are linked statically; the executable only retains the system C library as a dynamic dependency. Meson invokes `wayland-scanner` to generate protocol sources, so the recipe builds a static scanner from the official Wayland 1.24.0 source during the build.

Actual key injection requires a Wayland compositor that supports the virtual-keyboard protocol and an available Wayland socket. The tested HarmonyOS PC device did not provide one, so the recorded device validation covers compilation, package metadata, and pre-connection keysym handling.

## Dependencies

| Dependency | Version |
|---|---:|
| wayland | 1.24.0 |
| libxkbcommon | 1.8.0 |

## Usage

With a compatible Wayland compositor running, send a key using:

```sh
wtype -P A -p Return
```

See the installed `wtype(1)` manual for the full option list.

## References

- [Upstream source](https://github.com/atx/wtype)
- [wtype 0.4 release](https://github.com/atx/wtype/releases/tag/v0.4)
