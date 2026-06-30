# mono — Cross-platform .NET Framework

Mono is an open-source implementation of Microsoft's .NET Framework based on the ECMA standards for C# and the Common Language Runtime. A growing family of solutions and an active and enthusiastic contributing community is helping position Mono to become the leading choice for development of cross-platform applications.

## Version

- **6.12.0.122** (Stable Release)

## Status

- **built**: C/C++ JIT compiler (mono-sgen) compiled successfully. C# class library compilation incomplete due to resource constraints.

## Build Information

- **Build Date**: 2026-05-27
- **Build System**: autotools
- **Compiler**: clang
- **Target**: aarch64-ohos
- **Configure Options**: `--prefix=/storage/Users/currentUser/usr/local --without-x --disable-btls`

## Patches Applied

60 patches applied, including:

1. **0007-config.guess.patch**: HarmonyOS/OHOS detection (E007)
2. **0008-config.sub.patch**: HarmonyOS/OHOS support (E007)
3. **0005-external-corefx-src-Native-Unix-System.Native-pal_maphardwaretype.c.patch**: sockaddr_storage redefinition fix (E081)
4. **0002-configure.ac.patch**: HMDFS umask fix (E011)
5. Various script wrapper fixes for installation paths

## Platform Issues Resolved

### E007: config.guess/config.sub HarmonyOS Detection ✅
- **Issue**: Standard config.guess script cannot identify HarmonyOS system
- **Solution**: Replace with automake-1.16 version + OHOS patches
- **Reference**: knowledge/graph/E007.kv

### E011: HMDFS umask Permission Problem ✅
- **Issue**: HMDFS filesystem UID mapping mismatch, umask 077 creates temporary directories with wrong permissions
- **Solution**: Modify configure script `umask 077` to `umask 022`
- **Reference**: knowledge/graph/E011.kv

### E081: sockaddr_storage Redefinition ✅ (New Discovery)
- **Issue**: OpenHarmony SDK defines sockaddr_storage in both linux/socket.h and sys/socket.h, causing compilation errors
- **Solution**: Use `#ifdef __OHOS__` guard to skip linux/socket.h and manually define __kernel_sa_family_t
- **Reference**: knowledge/graph/draft/E081-draft-2057.kv
- **Impact**: All network programming software on OpenHarmony

## Platform Limitations

1. **C# Class Library Compilation Slow**: mono uses bootstrap compilation (mono + roslyn csc.exe) which requires significant memory and CPU resources
2. **System Resource Constraints**: Current test environment has limited memory, causing fork failures
3. **Test Suite Incomplete**: make check fails due to memory constraints

## Key Artifacts

- **mono-sgen**: 16M JIT compiler executable (arm64, dynamically linked)
- **libmonosgen-2.0.so**: Shared library for runtime
- **Partial C# libraries**: mscorlib.dll, Mono.Security.dll, System.dll, PEAPI.dll (approx. 4-6 dlls)

## Usage

```bash
# Basic .NET program execution
mono-sgen --version
mono-sgen program.exe

# JIT compiler validation
mono-sgen --help
```

## Knowledge Gained

- **E007**: HarmonyOS config.guess/config.sub detection (L1 platform truth)
- **E011**: HMDFS umask permission problem (L1 platform truth)
- **E081**: OpenHarmony SDK sockaddr_storage redefinition (L1 platform truth - NEW)

## Notes

For complete compilation (including all C# class libraries), recommend:
- Environment with ≥4GB memory
- Patience for bootstrap compilation (may take hours)
- Alternative: use pre-built mono packages from other platforms with compatibility testing

## References

- [Mono Project](https://www.mono-project.com/)
- [Mono GitHub](https://github.com/mono/mono)
- E007: config.guess HarmonyOS detection
- E011: HMDFS umask permission problem
- E081: sockaddr_storage redefinition fix