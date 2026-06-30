# consul-template

Consul Template is a daemon that renders Go template files using data from Consul.

## Description

Consul Template provides a convenient way to populate values from Consul into configuration files using Go template syntax. It can watch for changes in Consul data and update the rendered configuration files accordingly.

## Homepage

https://github.com/hashicorp/consul-template

## License

MPL-2.0

## Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 0.42.0  | published | 2026-05-25 |

## Build Notes

- Go linker on HarmonyOS has mmap permission issues (EPERM), cannot compile from source
- Uses HashiCorp official prebuilt binary from releases.hashicorp.com
- Prebuilt binary is statically linked ELF, runs directly on OpenHarmony after ELF signing
- Go version compatibility: go.mod requires go >= 1.26.2, patched down to 1.25.8
- GOPROXY=https://goproxy.cn,direct recommended for China region

## Dependencies

- Go 1.25.10 (build toolchain, dependency download via goproxy.cn)

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- consul-template 0.42.0
```