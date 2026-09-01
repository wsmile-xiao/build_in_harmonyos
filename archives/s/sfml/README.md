# SFML - Simple and Fast Multimedia Library

SFML is a cross-platform multimedia library that provides System, Window, Graphics, Audio, and Network modules.

## OpenHarmony PC Scope

The current OpenHarmony PC Conan package provides the baseline modules that can be built without extra platform backends:

| Module | Status | Notes |
| --- | --- | --- |
| System | Supported | Time, string, thread, and system utilities. |
| Network | Supported | TCP/UDP and IP address utilities. |
| Window | Disabled | SFML 2.x needs X11/DRM/UDev style windowing/input backends not available in the current OHOS CI image. |
| Graphics | Disabled | Depends on the Window module and a graphics context provider. |
| Audio | Disabled | Requires OpenAL, which is not available as a published baseline dependency. |

This is a path A baseline adaptation. It does not claim full SFML multimedia support on OHOS.

## Conan Usage

```cmake
find_package(SFML REQUIRED COMPONENTS system network)
target_link_libraries(app PRIVATE SFML::System SFML::Network)
```

## Version Status

| Version | Status | Date | Notes |
| --- | --- | --- | --- |
| 2.6.1.1 | partial | 2026-07-19 | Conan recipe for System and Network modules. |

## Upstream

- Homepage: https://www.sfml-dev.org/
- Source: https://github.com/SFML/SFML
- Documentation: https://www.sfml-dev.org/documentation/
