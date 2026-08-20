# NuGet

NuGet is the package manager for .NET. The NuGet Command Line Interface (CLI)
provides the ability to create, publish, and manage NuGet packages from the
command line.

This package contains the prebuilt NuGet.exe binary (v7.6.0) from
[nuget.org](https://www.nuget.org/), packaged as a Conan recipe.

## Binary Information

- **NuGet.exe**: PE32 x86, .NET Framework assembly
- **Size**: ~8.0 MB
- **License**: Apache-2.0
- **Source**: https://github.com/NuGet/NuGet.Client

## Platform Compatibility

NuGet.exe is a Windows PE32 executable. On HarmonyOS PC (aarch64 Linux),
it requires **mono** or a compatible .NET Framework runtime to execute.
The package includes a wrapper script that attempts to invoke the binary
via available runtimes.

## Usage

```bash
# After conan install
nuget <command> [options]
```
