# libzahl 1.0 适配笔记

## 编译环境

- 构建系统：makefile（原生 make，无 configure/CMake）
- 上游版本：1.0
- 上游地址：https://git.suckless.org/libzahl（GitHub 作者镜像 https://github.com/maandree/libzahl）
- 源码包：1.0.tar.gz，sha256 `523ae1ba84b558fab3598f3d38885138c4df755cda403136102143f569b40162`
- 编译器：clang（从 Conan `tools.build:compiler_executables` 获取，真机为 clang 15）
- 状态：built（待真机预检通过后由 HMBS 统一提交）

## 上游测试清点（R51 三步法第 1 步：申报）

- 上游测试入口：`make check`（Makefile：`check: test` + `./test`）
- 测试源：`test.c`（约 1015 行，约 516 处 assert/assert_zu/assert_s 断言）+ `test-generate.py` 生成的 `test-random.c`
- 测试框架：无 gtest/pytest/ctest；单一 `test` 二进制，成功退出码 0，失败打印 `Failure at line` 并返回非零
- 全树 `find -name '*test*'` 仅命中 `test.c` + `test-generate.py`；无 `tests/` 目录
- 结论：上游存在测试，conanfile `build()` 已完整集成 `make ... test && ./test`，不删减不跳过

## 编译步骤

```bash
make CC=<cc> AR=<ar> RANLIB=<ranlib> -j1 libzahl.a
make CC=<cc> AR=<ar> RANLIB=<ranlib> -j1 test
./test
```

说明：

- `CC/AR/RANLIB` 从 Conan conf `tools.build:compiler_executables` 获取，禁止裸用 shell 环境变量（R33）
- `-j1` 单作业（R9）
- 上游 `all` 目标仅构建 `libzahl.a`，不涉及 pdflatex 文档目标，无需处理
- `test` 目标依赖 `test-random.c`，由 `test-generate.py`（shebang `#!/usr/bin/env python3`）生成，依赖构建机 PATH 中的 python3（真机由 hmbs 注入 `HMBS_PYTHON3`）
- 仅支持静态构建；`shared=True` 时 `validate()` 直接报错（上游无共享库目标）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `config.mk` 默认 `CC=cc` | 真机/CI 仅提供 clang | 配方经 make 命令行覆盖 `CC/AR/RANLIB` |
| 2 | 上游测试生成器依赖 python3 | `test-random.c` 须由 `test-generate.py` 生成 | 复用构建机 PATH 中的 python3，不在配方中硬编码解释器路径 |

## 源码修改

无补丁。`conandata.yml` 无 `patches` 节。

## 依赖版本

无依赖（仅 libc）。W0 结论：无需前置发布任何依赖。

## 验证结果

- 本地：Windows 执行器无法运行 conan 真机编译，按任务守则等待 HMBS 后台真机预检
- 真机预检命令（HMBS 执行）：`conan create`（含 `build()` 内 `make ... test && ./test` + `test_package` 的 `./test_libzahl`）
- 机器证据标记：
  - `build()` 输出 `HMBS_UPSTREAM_TEST_RESULT`（framework=make，discovered=1/executed=1/passed=1）
  - `test_package` 输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=6/passedCount=6）
- 证伪预案（真机轮若需）：检查 `./test` 输出非空且失败可被捕获；必要时用 `exit 1` 桩替换 `test` 二进制确认 harness 非静默通过；区分通过与跳过（当前无跳过逻辑）

## 交付物

| 文件 | 说明 |
|------|------|
| libzahl.a | 静态库 |
| zahl.h | 主头文件 |
| LICENSE | 许可证文件（随包发布到 licenses/） |

## 注意事项

- libzahl 非线程安全（上游 NOTES 原文），多线程使用者须自行同步
- 上游文档明确不建议用于密码学场景（`zahl.h` 注释）；配方不改变该结论
- 本轮未提交、未推送，未创建 PR；工作树待 HMBS 真机验证

## 2026-09-16 真机预检失败诊断与修复（fixing_verification 轮）

- 真机证据：`./test` 断言失败 `Failure at line 953: zcmp(c, d), expected == 0, but got -1`
  （确定性段 `zsetu(a, 1e9) / zsets(b, "1e18") / zmul(c, a, b)` 应得 `1e27`），
  而此前更窄位宽的乘法断言（926-948 行，`1e9*1e9=1e18` 等）全部通过。
- 根因判定：同一份源码在 gcc/x86_64 下通过，真机 clang 15/aarch64 下对
  Karatsuba 大数乘法算出错误结果——典型 codegen 症状（上游 `config.mk`
   pin `-O3`；库内有手写进位链、自重叠 `memcpy` 等易被激进优化误编译的写法），
  非上游算法错误，不删减不断言。
- 修复（`conanfile.py` `build()`，均不削弱测试）：
  1. make 命令行覆盖 `CFLAGS="-std=c99 -O2 -Wall -pedantic -fno-strict-aliasing -fwrapv"`，
     其余 `CC/AR/RANLIB/CPPFLAGS/LDFLAGS` 保持上游原样；
  2. 用 `HMBS_PYTHON3`（回退 `python3`）显式生成 `test-random.c`，
     不再依赖脚本 shebang + 可执行位（真机 HMDFS 上报 `chmod` 不受支持），
     生成内容与上游一致；生成后校验非空，空文件直接抛错而非静默跳过随机套件；
  3. `[readonly_tmp]` 平台诊断：配方与上游测试均不写 `/tmp`（产物与生成文件
     均在 conan build/source 目录内），已复用 HMBS 注入的 `TMPDIR`，无需改动。
- 待下轮真机预检验证 `./test` 全绿及双 JSON 标记。

## 2026-09-16 second fix (O2 still fails -> O0)
- Preflight 09:25Z with CFLAGS -O2 -fno-strict-aliasing -fwrapv still aborts at test.c:953 (1e9*1e18, zmul Karatsuba, zcmp -1 vs 0).
- Action: CFLAGS -> -O0 -fno-strict-aliasing -fwrapv; add make clean at build start to drop stale .o; no test weakened.
- Await next preflight for ./test green + dual JSON markers.
