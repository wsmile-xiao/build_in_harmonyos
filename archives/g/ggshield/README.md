# ggshield

GitGuardian CLI application that runs in your local environment or in a CI environment to help you detect more than 500+ types of secrets.

- **Homepage**: https://github.com/GitGuardian/ggshield
- **License**: MIT
- **Category**: security
- **Build System**: Python (hatchling)

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 1.51.0 | published | 2026-06-11 |

## Installation

```bash
# Install via cmd-pkgs
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ggshield 1.51.0

# Then install runtime dependencies
pip install pygitguardian charset-normalizer click cryptography marshmallow pyyaml requests rich
```

## Notes

- ggshield is a pure Python project (no C extensions)
- Full functionality requires ~20 Python runtime dependencies
- Requires Python 3.9+ and git