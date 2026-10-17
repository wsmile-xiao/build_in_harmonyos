# slop

slop (Select Operation) is a C++ command-line utility and library for interactively selecting an X11 screen region.

## Features

- Select a window or a rectangular screen region.
- Print geometry, coordinates, window ID, and cancellation state.
- Expose both C and C++ selection APIs.
- Provide an XShape renderer when OpenGL acceleration is unavailable.

## HarmonyOS adaptation

The HarmonyOS build uses the upstream XShape backend and disables the optional GLX acceleration path because HarmonyOS PC does not provide a GLX display stack. X11 headers and libraries are supplied entirely by Conan packages. Non-interactive commands such as `--version` and `--help`, the public defaults API, and the deterministic no-display error path are covered by the consumer tests.

## Dependencies

- libx11/6.4.0
- libxext/6.4.0.1
- glm/1.0.3

## References

- https://github.com/naelstrof/slop
