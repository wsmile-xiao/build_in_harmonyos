# iucode-tool

`iucode-tool` parses, filters, validates, and repackages Intel IA32/x86_64
microcode bundles.

- **Homepage**: https://gitlab.com/iucode-tool/iucode-tool
- **License**: GPL-2.0-only
- **Versions**: 2.3.1
- **HarmonyOS PC note**: the arm64 build keeps offline microcode parsing and
  output operations. The upstream x86 CPUID scan and Linux cpuid-device path
  are disabled rather than represented as working Intel hardware support.
