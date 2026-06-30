# mongooseim

## What is it?

MongooseIM is an Erlang/OTP-based XMPP messaging server designed for robustness, scalability, and efficiency. It is developed by Erlang Solutions and supports enterprise messaging features.

## Key Features

- Erlang/OTP-based architecture for high concurrency
- XMPP protocol support with extensions
- Scalable to millions of concurrent connections
- Built-in support for pubsub, HTTP upload, external service discovery

## OHOS/HarmonyOS Adaptation

- **Build type**: makefile (Erlang/OTP rebar3-based)
- **7 patches required** for platform compatibility
- Patches modify rebar.config and Erlang source files for musl/HMDFS compatibility

## Version 6.7.0

- Status: published
- Build date: 2026-06-08
- 7 patches applied for Erlang module compatibility