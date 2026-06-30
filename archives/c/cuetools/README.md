# cuetools

cuetools 是一组用于处理 .cue 和 .toc 文件的工具集，这些文件常用于描述 CD/DVD 光盘镜像的轨道结构。

## 主要工具

- **cuebreakpoints**: 从 .cue/.toc 文件中提取轨道断点时间
- **cueconvert**: 在 .cue 和 .toc 格式之间相互转换
- **cueprint**: 打印碟片和轨道信息（表演者、标题、曲目数等）
- **cuetag**: 基于 cue/toc 文件信息为音频文件打标签（shell 脚本）

## OHOS 适配要点

1. **HMDFS 文件权限问题**: HMDFS 文件系统上 `mktemp -d` 使用 umask 077 创建的目录被 UID 20001006 拥有，而进程 UID 为 20020082，导致目录内文件无法写入。解决方案：将 umask 从 077 改为 007，并添加 `chmod g+rwx "$tmp"`。
2. **ELF 签名阻止 configure 测试**: 鸿蒙系统要求 ELF 二进制签名后才能执行，configure 的 conftest 测试程序无法运行，导致误判为交叉编译。解决方案：修改 configure 脚本跳过运行时检测（`if false` 替代 `if test "$cross_compiling" != yes`）。
3. **lld 链接器不可用**: lld 因依赖 libxml2.so.16（缺失）而失败。解决方案：使用 `LDFLAGS=-fuse-ld=bfd` 替代 lld 链接器。
4. **需要 autoreconf 生成构建文件**: 源码 tarball（GitHub release）仅含 configure.ac，不含 configure 和辅助脚本，需运行 `autoreconf -fi` 生成。补丁集包含所有 autoreconf 生成的文件。

## 依赖关系

- 无编译依赖，无运行依赖
- 仅依赖 musl libc (libc.so)

## 版本说明

- configure.ac 声明版本为 1.4.0，GitHub release tag 为 1.4.1
- `-V` 输出为 `cuetools 1.4.0`，这是上游设计

## 参考资料

- 源码仓库: https://github.com/svend/cuetools
- 许可证: GPL-2.0-only