# paho.mqtt.cpp

Eclipse Paho C++ client library for the MQTT protocol.

This package builds the C++17 client library against the repository's
`paho.mqtt.c/1.3.14` package. The default recipe configuration is static,
without SSL, and without samples, examples, or documentation. Upstream
Catch2 tests are enabled; OHOS runs the non-broker cases and explicitly
filters cases tagged `[broker]` when no reachable MQTT broker is available.
The Conan test package also includes an OHOS-only runtime/consumer check that
verifies the HarmonyOS platform identity and Paho client initialization.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.6.0 | built | Static C++ library, no SSL; upstream Catch2 tests enabled |

## Homepage

https://github.com/eclipse/paho.mqtt.cpp
