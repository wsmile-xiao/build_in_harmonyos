# starfetch

starfetch is a command line tool written in C++17 that displays a random or
named constellation together with its informational data.

## Package contents

- Executable: `bin/starfetch`
- Resource data: `share/starfetch/constellations`, `share/starfetch/template`,
  `share/starfetch/help_message.txt`
- License: GPL-3.0

## OpenHarmony adaptation

- Compiles the single upstream source file with the profile C++ compiler; the
  upstream `make install` target (hardcoded /usr/local) is not used.
- Adds the `STARFETCH_RES_DIR` environment override so the packaged resources
  are found regardless of install prefix (exported via `runenv_info`).
- Upstream ships no test suite, so a 19-assertion consumer test validates the
  installed executable, resources, and CLI behavior.
- No Conan dependency; nlohmann/json is vendored upstream.

## Usage

```sh
starfetch            # random constellation
starfetch -n orion   # specific constellation
starfetch -l         # list available constellations
starfetch -c red -n orion
```

Upstream: https://github.com/Haruno19/starfetch
