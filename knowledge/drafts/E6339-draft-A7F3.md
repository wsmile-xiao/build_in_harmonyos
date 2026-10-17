# E6339-draft-A7F3：Qt 共享库 SONAME 软链接在 HarmonyOS PC 存储环境受限

> 状态：DRAFT
> 来源：`qtdeclarative` 6.11.1.1 适配 PR #7677
> 贡献者：AtomCode
> 更新：2026-09-08

## 现象

Qt 6 模块的 CMake 规则会为带 `VERSION` 或 `SOVERSION` 的共享库生成
SONAME 别名，例如 `libQt6Core.so`、`libQt6Core.so.6` 和带完整版本号的
文件之间的软链接。在 HarmonyOS PC 真机的受限存储环境中，生成这些链接
可能出现：

```text
cmake_symlink_library: System Error: Permission denied
Operation not permitted
failed to create symbolic link
```

该错误发生在构建或安装输出的别名生成阶段。它不等同于 Qt 源码编译失败，
也不等同于缺少 Qt 的 ABI 依赖。

## 根因

受限设备存储，特别是具有 HMDFS 语义的路径，对软链接创建和链接目标操作
有额外限制。Qt 的标准 CMake 安装逻辑假定宿主文件系统允许完整的
SONAME 软链接链，因此同一套规则在普通 Linux 文件系统可用，在设备构建
树或包目录中可能失败。

这是一类文件系统能力差异。它影响的是库文件别名的产生，不应通过修改
源码 ABI、删除依赖或把错误改成警告来掩盖。

## 推荐方案

只在 HarmonyOS PC 的 Qt 适配构建路径中处理生成的链接规则：

1. 定位 CMake 生成的 `cmake_symlink_library` 或等价别名规则。
2. 将需要交付的 SONAME 别名物化为普通文件复制，或者在受控的打包步骤
   中生成可验证的普通文件别名。
3. 保留真实 ELF 文件，并用 `readelf -d` 检查 `SONAME` 和 `NEEDED`。
4. 构建和打包完成后检查包内没有未处理软链接；若某个别名不是交付必需，
   应明确记录省略原因。

推荐方案只处理生成的输出别名，不修改 Qt 的公共 ABI，也不改变正常桌面
平台的默认打包行为。

## 验证

在同一设备和同一构建树上执行：

```sh
grep -R "cmake_symlink_library" "${BUILD_DIR}"
find "${PACKAGE_FOLDER}" -type l -print
readelf -d "${PACKAGE_FOLDER}/lib/libQt6Core.so" | grep -E "SONAME|NEEDED"
```

通过条件是：构建和包生成不再因软链接规则失败，交付目录包含预期的真实
Qt ELF 库和可用别名，`readelf` 能读到正确的动态段，并且没有把未创建的
链接计入交付文件。

## 与现有知识的关系

- `DRAFT-expat-cmake-soname-1912` 和
  `DRAFT-openjpeg2-hmdfs-versioned-soname` 记录了通用 SONAME 软链接在
  HarmonyOS 存储环境中的同类限制。本草稿补充 Qt 6 CMake 输出、Qt 库别名
  和 Conan 配方验证边界。
- `E326` 涉及设备文件系统权限和链接规则。本草稿聚焦 Qt 共享库的
  `VERSION/SOVERSION` 别名物化，不覆盖脚本执行权限或 `/bin/sh` 兼容性。

## 禁止做法

- 不要忽略 `cmake_symlink_library` 错误后继续报告构建通过。
- 不要只用 `chmod` 试图改变软链接能力。
- 不要为了让日志变绿而跳过 SONAME、真实 ELF 或包内链接审计。
- 不要把宿主机 Linux 文件系统上的结果直接当作 HarmonyOS PC 真机证据。

## 来源与边界

本草稿来自 PR #7677 的 Qt 6.11.1.1 适配过程。它描述的是 HarmonyOS PC
受限存储上的构建/安装边界，不代表所有 HarmonyOS 存储路径都禁止软链接，
也不要求对不需要 SONAME 别名的静态构建强行复制文件。
