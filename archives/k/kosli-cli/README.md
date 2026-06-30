# Kosli CLI

## Description

Kosli CLI is a command-line client for reporting compliance events to the Kosli platform. Kosli is an SDLC governance platform that automates controls, evidence, and audit trails for regulated industries.

## Features

- Report artifact provenance and compliance events
- Attest various types of evidence (Jira, JUnit, etc.)
- Create and manage flows and trails
- Integration with CI/CD pipelines

## OHOS Adaptation

### Key Points

1. **Precompiled Binary**: Kosli CLI is distributed as a statically-linked Go binary. Due to the OpenHarmony ELF signing requirements and the Go toolchain bootstrap circular dependency issue, we use the official precompiled binary.

2. **ELF Signing**: The binary must be signed using `binary-sign-tool` before it can run on OpenHarmony:
   ```bash
   /data/service/hnp/bin/binary-sign-tool sign -inFile kosli -outFile kosli-signed -selfSign 1
   chmod a+x kosli-signed
   ```

3. **Go Toolchain Issue**: Go 1.26.4 requires a signed bootstrap Go >= 1.22.6 to compile from source. The `binary-sign-tool` refuses to sign externally downloaded Go binaries, creating a circular dependency. This prevents local compilation of Go software on OpenHarmony.

## Dependencies

- None (static binary)

## References

- Official: https://kosli.com
- GitHub: https://github.com/kosli-dev/cli