# kconfig-frontends

Standalone Linux-style Kconfig parser and text-based configuration frontends
for projects that use Kconfig outside the Linux kernel tree.

## Included tools

- `libkconfig-parser` and its public Kconfig headers
- `kconfig-conf` for non-interactive configuration generation
- `kconfig-mconf` and `kconfig-nconf` for terminal menu configuration

The GTK and Qt frontends and the upstream helper scripts are outside this
HarmonyOS package's approved scope.

## HarmonyOS adaptation

The package is intended for HarmonyOS PC arm64. It builds the ncurses
dependency statically so a package-local curses library cannot shadow the
system library. Configure and make are driven with the available Bash
executable, and build temporary files stay below Conan's build folder. The
OHOS Conan consumer test exercises parser/config read-write under `$HOME/tmp`
and launches both terminal frontends through a PTY.

## Dependencies

- Build/runtime: `ncurses/6.6`
- Build tools: Autoconf, Automake, Libtool, M4, Bison, Flex, and Gperf Conan
  packages (see the version recipe for exact references).

## References

- Upstream: <https://gitlab.com/ymorin/kconfig-frontends>
- Version recipe: `4.11.0.1/`
