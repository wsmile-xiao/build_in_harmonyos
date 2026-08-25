# Synergy Core

Synergy Core is the command-line service behind Synergy, a tool for sharing a
keyboard and mouse between computers over the network.

## Features

- Runs as either a Synergy server or client from one unified executable.
- Transfers keyboard, pointer, wheel, hotkey, and clipboard events.
- Preserves the upstream encrypted transport through an OpenSSL-compatible
  provider.
- Supports multiple displays and the Synergy wire protocol.

## OpenHarmony Adaptation

The OpenHarmony backend uses InputKit for global input monitoring,
interception, and injection. Display geometry comes from the native display
manager, while clipboard exchange uses the native pasteboard and UDMF APIs.
The package builds the unified command-line service without Qt, X11, DBus, or
the desktop GUI.

Input injection remains subject to the platform's user authorization policy.
The backend reuses an authorization request that is already pending and does
not revoke the system-wide authorization when the service is disabled.

The OpenHarmony source selection and native-library linkage are verified. The
runtime cross-device input and clipboard paths, primary-screen interceptor,
display hotplug, hotkey, and screensaver workflows are not yet closed by the
current validation evidence.

GoogleTest 1.17.0 is fetched only to build and run the upstream test suite. It
is not declared as a package dependency and is not included in the package.

## Dependencies

- `aws-lc/5.5.0` for the OpenSSL-compatible TLS implementation.
- `synergy-extra` at the upstream-pinned commit, fetched as source during the
  build.
- OpenHarmony native InputKit, display-manager, pasteboard, and UDMF APIs.

## References

- [Synergy](https://symless.com/synergy)
- [Source repository](https://github.com/symless/synergy)
