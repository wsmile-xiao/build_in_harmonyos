# ocmtoc

Mach-O to PE/COFF converter (`mtoc`), used in
[Acidanthera UDK](https://github.com/acidanthera/audk) and
[EDK II](https://github.com/tianocore/edk2).

- 上游仓库：<https://github.com/acidanthera/ocmtoc>
- 当前适配版本：1.0.4（上游 tag `1.0.4`，cctools 1024.3 rebase）
- 产物：`bin/mtoc` 命令行工具 + `share/man/man1/mtoc.1` 手册页
- 构建方式：custom（直接用 clang 编译 `efitools/mtoc.c` 及所需 `libstuff`
  子集；上游仅提供 Xcode 工程，无 CMake/autotools/meson）
- 许可：APSL-2.0

详见各版本目录下的 `notes.md`（适配审计、移植说明、验证记录）。
