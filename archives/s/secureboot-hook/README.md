# secureboot-hook

Void Linux kernel hook that generates a signed UKI (Unified Kernel Image) for secure boot. Pure shell script project with no compilation needed.

- Homepage: https://github.com/spflaumer/secureboot-hook-void
- Pure shell-based tool (no C compilation needed)
- Installs hook script to `etc/kernel.d/post-install/30-secureboot` and config to `etc/kernel.d/secureboot.conf`
- Runtime dependencies: dracut, sbctl, binutils (Void Linux specific)
