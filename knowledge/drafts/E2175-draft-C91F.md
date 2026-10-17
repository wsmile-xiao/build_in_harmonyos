# E2175 - 含空格 sysroot 在多层编译 flag 中必须保留单一 argv 边界

> Status: DRAFT | category: cross-compile, Conan, CMake, Windows

## 问题现象

Windows 主机使用 Conan 生成 OHOS 交叉编译环境时，SDK sysroot 位于含空格
目录。profile 中能看到完整的 `--sysroot="..."`，但配置探针或正式编译仍报告
找不到头文件、路径片段被当作未知参数，或者笼统地显示
`C compiler cannot create executables`。

## 根因

`tools.build:cflags/cxxflags` 中的值不是直接传给 `execve` 的 argv 数组。它依次
经过 Conan 配置解析、buildenv 脚本生成、CMake toolchain 拼接和 Ninja 命令行
解析。为其中一层手工加入的嵌套引号可能在下一层被去掉或再次转义，导致 clang
最终收到多个参数。配置文件里“肉眼可见完整路径”并不能证明最终 argv 边界。

本次 InChI 构建中，Windows SDK 原始 sysroot 位于含空格路径。两种 profile
引号写法均未得到稳定的编译器参数；把同一冻结 sysroot 复制到任务私有的
无空格路径后，Conan/CMake/Ninja 完成了 132 个编译步骤。

## 修复步骤

1. 在 `F:/HarmonyPC/<task-unique-dir>` 下创建任务私有、无空格的
   `toolchain-local/sysroot`；逐级确认父路径不是 reparse point。
2. 从只读 SDK sysroot 逐文件复制，不创建 junction 或符号链接；记录文件数、
   总字节数和 reparse point 数。
3. 在 Conan 的结构化 flag 列表中把
   `--sysroot=F:/HarmonyPC/<task>/toolchain-local/sysroot` 作为一个元素，不把
   多个 flag 拼成一段复合 shell 字符串。
4. 若构建集成支持结构化 `CMAKE_SYSROOT` 字段，优先使用它；但仍需检查最终
   verbose 编译命令，因为生成器可能再次转换参数。

## 验证方式

- 核对投影 inventory：本次为 2412 个文件、52478277 bytes、0 个 reparse
  point；来源与目标内容按任务证据绑定。
- 检查生成的 buildenv、CMake/Ninja verbose 命令或 `compile_commands.json`，
  确认每条 clang 命令只有一个完整 `--sysroot=<absolute-path>` 参数。
- 执行真实交叉构建，而不只运行配置解析；本次 132 个步骤全部通过。
- 对产物执行 ELF 检查：目标必须为 AArch64，且 RPATH/RUNPATH、SONAME 和
  NEEDED 闭包满足配方合同。
- 最终仍需真机执行消费者与上游测试；参数修复本身不等于目标验证通过。

## 无效方案

- 在 profile 字符串中继续叠加单引号、双引号或反斜杠：这只改变某一解析层，
  不能证明最终 argv，且不同 PowerShell/Python/CMake 版本可能产生不同结果。
- 用 junction/symlink 制造短路径：会跨越任务根与 reparse-point 安全边界，
  也使 SDK 来源和清理目标难以证明。
- 只看 `conan install` 成功：install 只证明依赖图和生成器执行，未证明 clang
  真正消费了正确 sysroot。

## 适用范围

适用于 Windows 主机上的 Conan + CMake/Meson/Ninja 交叉编译，以及任何把
含空格路径嵌入 `-I`、`-L`、`--gcc-toolchain`、`--sysroot`、linker flag 后再
跨越多层字符串序列化的构建链。

## 不适用范围与安全边界

- 若底层 API 从始至终使用结构化 argv 且有实际命令证据证明路径未被拆分，
  无需复制 sysroot。
- 不得修改共享 SDK、全局 Conan profile 或系统环境来修复单个任务。
- 不得借此把 SDK、缓存或可重建制品写到 `F:/HarmonyPC` 之外。
- 投影成功仅解决参数边界；源码身份、依赖 RREV/PID/PREV、目标 ELF、真机
  测试和 release/postrelease 仍需独立验证。

## 与现有知识的差异

四个强制范围以 `sysroot + space/quote`、`CMAKE_SYSROOT`、`compiler flag +
space` 和 `nested quote` 查询均无命中。本条目聚焦“多层字符串序列化破坏单一
argv 元素”与任务私有无空格投影，不重复一般性的 SDK 缺失、编译器选择或
Conan profile 配置知识。
