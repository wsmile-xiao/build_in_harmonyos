# perl-ipc-run3

IPC::Run3 - Perl module for running subprocesses with I/O redirection

## Description

IPC::Run3 is a pure Perl module that provides a simple interface for running subprocesses with I/O redirection. It is widely used in Perl system programming and test automation.

**Key Features:**
- Simple subprocess execution with I/O redirection
- Support for stdin/stdout/stderr capture
- File redirection support
- Environment passthrough
- Pure Perl implementation (no XS/C code)

## Homepage

https://metacpan.org/pod/IPC::Run3

## Available Versions

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 0.049-r1 | 2026-06-12 | ✅ published | Pure Perl module, all tests passed, fully functional on OpenHarmony |

## Test Results

| Test Type | Result | Details |
|-----------|--------|---------|
| Unit Tests | PASS ✅ | 13/13 files, 69 test cases |
| Functional Tests | PASS ✅ | 8/8 scenarios verified |
| Stress Tests | PASS ✅ | 100/100 calls in 2 seconds |

### Verified Features

1. ✅ Module loading (version 0.049)
2. ✅ stdout capture from subprocesses
3. ✅ stdin pipe to subprocesses
4. ✅ File output redirection
5. ✅ stderr capture
6. ✅ Large output handling (1000+ lines)
7. ✅ Environment passthrough
8. ✅ Binary data handling

## Usage

After installation, the module can be used in Perl scripts:

```perl
use IPC::Run3;

# Run command and capture output
my @cmd = ("echo", "Hello");
my ($out, $err);
run3 \@cmd, undef, \$out, \$err;

# Pipe input to command
my $in = "test data";
run3 ["cat"], \$in, \$out;
```

## Build Information

- **Build System**: Perl (Makefile.PL)
- **Dependencies**: Perl 5.42.0
- **Platform**: aarch64-unknown-linux-ohos
- **Compiler**: clang 18.1.8
- **Package Size**: 55KB (pure Perl files)

## Installation

Install via cmd-pkgs:

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-ipc-run3 0.049-r1
```

Or manually copy to Perl's @INC path:
```bash
tar -xzf perl-ipc-run3-0.049-r1-ohos-aarch64.tar.gz
cp -r lib/site_perl/5.42.0/IPC /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/
```

## Notes

- ✅ Pure Perl implementation, no XS/C code
- ✅ No platform-specific adaptations needed
- ✅ No SELinux/HMDFS restrictions (pure Perl)
- ✅ Ready for production use on OpenHarmony

## Compatibility

| Platform | Status |
|----------|--------|
| OpenHarmony (aarch64) | ✅ Fully functional |
| HarmonyOS NEXT | ✅ Compatible |
| musl libc | ✅ No dependencies |