# hcloud

Hetzner Cloud CLI tool - command-line interface for managing Hetzner Cloud resources.

## Description

hcloud is a command-line tool for interacting with the Hetzner Cloud API. It allows you to manage servers, volumes, networks, and other cloud resources.

## Build Information

- Version: 1.57.0-r5
- Build System: Precompiled binary (Go)
- Architecture: arm64
- License: MIT

## Installation

Download the precompiled package from cmd-pkgs repository.

## Usage

```bash
hcloud version
hcloud server list
hcloud server create --name my-server --type cx22 --image ubuntu-22.04
```

## References

- GitHub: https://github.com/hetznercloud/cli
- Documentation: https://docs.hetzner.com/cloud/cli
