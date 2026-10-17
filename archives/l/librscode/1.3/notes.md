# librscode 1.3 适配笔记

## 编译环境
- 构建系统: custom（绕过上游 Makefile，由 Conan 配方直接编译）
- 编译日期: 2026-09-14
- 编译器: clang/clang++（OHOS 工具链，经 `tools.build:compiler_executables` 注入）
- 状态: built

## 编译步骤

1. 下载源码: https://downloads.sourceforge.net/project/rscode/rscode/1.3/rscode-1.3.tgz（sha256 `0d79ee8b9a975e4c7ee542e64f96e65c106e40b97b711fc683b3c725f8f9a5fe`）
2. Conan 配方 `conanfile.py` 绕过上游 Makefile，直接编译四个上游 C 源文件（`rs.c`、`galois.c`、`berlekamp.c`、`crcgen.c`）并归档
3. 静态构建产出 `libecc.a`；共享构建产出 `libecc.so`（相对 SONAME）
4. `validate()` 限制仅 Linux/OHOS 平台构建
5. `test_package` 编译 `test_rscode.c`、链接 `libecc` 并在真机运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无法用 OHOS 工具链构建 | 上游 Makefile 硬编码 `gcc`/`ar`，假定宿主 GCC 环境 | 配方内 `_resolve_cc`/`_resolve_ar` 从 `tools.build:compiler_executables` 读取 OHOS 工具链（含可执行性校验与 PATH 回退），绕过 Makefile 直接编译源文件 |
| 2 | 无可执行的上游测试 | rscode 1.3 仅含 4 个 C 源码、ecc.h、example.c 演示程序与极简 Makefile，无测试框架 | 新增 `test_package/test_rscode.c` 消费者视角功能测试，12 个断言覆盖核心功能 |

## 源码修改

无。适配未修改上游任何源码文件（`patches_applied: []`）。

## 依赖版本

无第三方编译依赖（`dependencies: []`）。

## 验证结果

```text
CI 构建 #47245（OpenHarmonyPCDeveloper-CI-020，commit cee64db97e84）:
  Conan test_package: 通过
  L0 门禁（结构完整性）: 通过
  L1 门禁（测试执行验证）: 通过

test_rscode 断言: 12/12 通过（100%）
  覆盖: initialize_ecc 建表、编解码往返、单字节纠错、单擦除纠正、
        crc_ccitt 确定性、galois 域恒等式

真机验证: 通过（HMBS 真机预检）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `libecc.a` | 静态库 |
| `libecc.so` | 共享库（相对 SONAME） |
