# bore-cli

A modern, simple TCP tunnel in Rust that exposes local ports to a remote server, bypassing standard NAT connection firewalls.

## Description

bore-cli is a Rust-based CLI tool for creating TCP tunnels. It allows you to expose local ports to a remote server, similar to ngrok or localtunnel, but with a focus on simplicity and efficiency. bore is intended to be a highly efficient, unopinionated tool for forwarding TCP traffic to remote servers.

## Project

- **Source**: https://github.com/ekzhang/bore
- **License**: MIT
- **Language**: Rust
- **Build System**: Cargo

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 0.6.0 | built | 2026-06-18 |

## Binary

The binary produced by bore-cli is named `bore`. Usage:

```bash
# Start local client (forward local port to remote server)
bore local <local-port> --to <remote-host>:<remote-port>

# Start server on remote machine
bore server <port>
```

## Build Notes

- Rust project: use `cargo build --release` instead of `./configure && make`
- Requires `cargo update` to fix socket2 v0.4.9 compatibility issue on OpenHarmony (IovLen type not found)
- Source available as .crate file from crates.io mirrors
