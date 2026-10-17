# autobahn-cpp

Autobahn-C++ is a header-only C++ client library for the WAMP messaging protocol.
It provides session, call, publish/subscribe, authentication, raw socket, and
WebSocket++ transport APIs over Boost.Asio.

The HarmonyOS package uses Conan-managed Boost, OpenSSL, MessagePack-C++, and
WebSocket++ dependencies. The packaged headers are adapted for modern
Boost.Asio, where `io_service` and `io_service.hpp` were removed; the optional
upstream examples are not packaged because they require a live WAMP router.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 17.5.1-git7cc5d37 | built | 2026-08-31 |
