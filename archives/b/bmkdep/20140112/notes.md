# bmkdep 20140112 HarmonyOS 适配笔记

## 上游与构建系统

- 官方源码：GitHub 标签 `20140112`，提交 `53d9b7c553224e073ddea1271fe34be36837979c`
- 源码包 SHA256：`b80039dc18ec070886e21e3c1ea4a16fc60c239bb922add8c70838d982598635`
- 主体语言：C（`mkdep.c`、`findcc.c`，语言预检占比 100%）
- 上游 Makefile 依赖 BSD `bsd.prog.mk`；实际程序仅由两个 C 文件组成，因此配方使用 Conan 提供的 clang 直接编译。
- 外部依赖：无，仅使用系统 libc/POSIX 接口。

## HarmonyOS 适配

1. `findcc.h` 增加通用 `#ifndef DEFAULT_CC` 保护，使配方可将默认运行时编译器从 `cc` 设为 HarmonyOS SDK 提供的 `clang`；用户设置的 `CC` 环境变量仍拥有最高优先级。
2. `mkdep.c` 在系统 `<paths.h>` 加载后支持通过 `BMKDEP_PATH_TMP` 覆盖 `_PATH_TMP`，使未设置 `TMPDIR` 时可靠回退到 `/data/local/tmp`，避免只读 `/tmp`。
3. 同一通用机制允许通过 `BMKDEP_PATH_DEFPATH` 补充 HarmonyOS 常用编译器搜索路径；未引入 `__OHOS__` 源码分支，非 HarmonyOS 构建行为不变。
4. 输出为 PIE 可执行文件并启用 RELRO/NOW。

## 上游测试清点（R51）

| 项目 | 结果 | 证据 |
|---|---:|---|
| `tests/` 目录 | 0 | 标签源码树仅含 `ChangeLog`、`Makefile`、`bmkdep.1`、`findcc.c`、`findcc.h`、`mkdep.c` |
| 测试风格文件 | 0 | 递归检索 `test*`、`*_test.*`、`*.t` 无结果 |
| Makefile `test`/`check` 目标 | 0 | Makefile 仅声明 `PROG`、`SRCS`、安装目录并包含 `bsd.prog.mk` |
| 注册测试数 | 0 | 上游未使用 CTest、pytest 或其他测试注册框架 |

上游测试总数 N=0，实际可运行数 N'=0，通过率不适用。具体原因是标签源码未提供测试文件或测试目标，并非因缺少本地环境而跳过。消费者侧由 `test_package/test.sh` 提供 6 个通用行为断言；`test_package/test_harmonyos.sh` 另提供 1 个鸿蒙专项断言，真实验证未设置 `CC` 时的默认 `clang` 选择，并通过鸿蒙沙箱内可写的 `TMPDIR` 完成临时依赖生成。

## 验证计划

- `conan create`：在仓库正式 OHOS/aarch64 profile 上执行，覆盖干净源码下载、补丁、编译、打包和 `test_package`。
- 本地 CI：执行 `ci/conan/build_and_test.sh bmkdep/20140112`，保留 L0-L5 门禁结果。

## 验证结果

- 仓库本地 CI：`build_and_test.sh` 定向验证 `bmkdep/20140112`，G0、KC、JC、L0、L1、L1e、L2、L4、L5 全部通过，1/1 包成功。为避免污染用户保留的其他本地改动，JC 使用仅包含本软件 13 个交付文件的任务差异清单。
- Conan 消费测试：Linux 本机构建环境运行 6/6 通用断言通过，包括默认编译器调用和头文件依赖发现；L1e 移除 `bin/` 后反向测试按预期失败，证明测试实质依赖制品。
- HarmonyOS 专项测试：HarmonyOS 6.0 PC x86_64 虚拟机运行 1/1 断言通过；测试显式取消 `CC`，确认制品选择默认 `clang`，并使用运行环境提供的可写沙箱 `TMPDIR` 完成临时依赖生成。
- 正式架构构建：HarmonyOS SDK 26.0.0 / clang 15.0.4 按 `os=OHOS`、`os.version=6.0`、`arch=armv8` 完成 `conan create`。最终 ARM64 产物 SHA256 为 `13a0ba77fa5083adde81d0224175b09d878b40bdad04beead326cdfbe494cf10`，是 AArch64 PIE，GNU_STACK 为 RW（不可执行），启用 RELRO+NOW，仅 `NEEDED libc.so`，并包含 `/data/local/tmp` 与默认 `clang` 适配值。
- 仓库 `conan-verify`：G1-G4 通过；该本地工具未能从 Conan 2 缓存解析包路径，报告中的 L2/L4/L5 显示跳过，但相同门禁已由 `build_and_test.sh` 独立通过，ARM64 ELF 属性也已用 SDK `llvm-readelf` 单独核验。
