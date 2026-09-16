# libequihash 1.0.10 — 适配笔记

> 适配日期: 2026-09-14
> 适配人: momimgya（队伍：干）
> 状态: built（待真机 conan create 全量验证）
> 构建系统: 纯 Makefile（无 configure）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libequihash |
| 版本 | 1.0.10（首次适配，无后缀） |
| 构建系统 | Makefile |
| 上游仓库 | https://github.com/stef/equihash |
| 上游版本 | v1.0.10 tag |
| 源码 | https://github.com/stef/equihash/archive/refs/tags/v1.0.10.tar.gz |
| sha256 | f48ed2d62abc94389b3bb1c612e733ce80107b058513a3e5611df1021140b971（27397 字节实测） |
| 许可证 | CC0-1.0 |
| 依赖 | 无外部依赖（上游唯一的 libsodium 调用已内聚，见“三、配方设计”） |

## 二、上游测试审计（确无测试套件）

解包官方 `v1.0.10.tar.gz`（共 13 个文件）逐项核查：

| 检查项 | 结果 |
|--------|------|
| Makefile 的 check/test 目标 | 无（目标仅 all/android/clean/install） |
| tests/ 或 test/ 目录 | 无 |
| ctest / meson test / pytest 注册 | 无 |
| `python/test.py` | 仅 4 行绑定用法演示（solve+verify 打印，无断言，需另行构建扩展模块），不构成测试套件 |
| `bench.cc` | 性能基准（输出耗时），非断言测试；上游 v1.0.5 起已将其排除出默认构建 |

结论：上游无可接入的测试套件。`test_package/MANIFEST.yml` 按规范写入
`upstream_tests_exist: false` 与完整 `upstream_test_audit`，
`test_package/conanfile.py` 在每次运行都输出 `status:"no_tests"` 的
`HMBS_UPSTREAM_TEST_RESULT` 标记（含具体 reason）。

## 三、配方设计

- 无外部依赖：上游对 libsodium 的唯一使用是
  `crypto_generichash(out, outlen, in, inlen, NULL, 0)`（两处调用），即 keyless
  BLAKE2b。`vendor/blake2b.{h,c}` 是按 RFC 7693 自包含实现的等价哈希（CC0，
  与本库同许可证），`patches/0002` 把 `equihash.cc` 的 `#include <sodium.h>`
  替换为内聚头文件加同名 inline  wrapper，PoW 语义逐比特不变。
  选内聚而非换依赖版本的原因：真机实测 `libsodium/1.0.20` 与 `1.0.22` 均从
  conancenter 取配方在预检机从源码重编，其 configure 按 profile 的
  `CONFIG_SHELL=/data/service/hnp/bin/bash` 重执行，而该路径在预检机上
  inaccessible（`configure[139/142]: ... not found`，exit 127），且 ohpcd 远端
  无对应 OHOS 预编译包可复用；内聚后构建全程只有 `cc/c++/make/ar`，不再经过
  任何 Autotools configure。
- `source()` 把 `vendor/` 拷贝进源码树；`build()` 先用 CC 编出 `blake2b.o`，
  再 `make LIBS="" EXTRA_SOURCES="blake2b.o"`（命令行变量覆盖上游写死的
  `LIBS=-lsodium`），`.so` 直连该对象；上游静态库规则只归档 `equihash.o`，
  构建后用 `ar rcs libequihash.a blake2b.o` 追加，保证静/动态产物都自包含。
- `build()` 显式传 `SYS="aarch64-linux-ohos"`，使 make 不执行 `gcc -dumpmachine`
  探测（OHOS 上无 gcc；该探测只控制 x86 专用的 `-fcf-protection=full`）。
- 只构建 `libequihash.so libequihash.a` 两个库目标：`equihash` CLI 的链接行需要
  `-lstdc++`，OHOS clang/libc++ 工具链不提供；bench/CLI 不打包，包保持纯库形态
  （R38：无需 commands.json）。
- `package()` 拷贝 `equihash.h`、`LICENSE`、静态库；`shared=True` 时追加 `.so`
  并创建 `libequihash.so.0` 程序链接名（symlink，失败回退为复制）。
- R33：CC/CXX/AR 全部取自 `tools.build:compiler_executables`（AR 缺失时按
  `ar`/`llvm-ar` 可用性回退）；`self.run()` 中无 `${CC}` 类裸变量。
- R32：`validate()` 用 `in ("Linux", "OHOS")`。
- 非系统同名库：`libequihash.so` 与系统库无冲突，shared/static 均保留。

## 四、补丁清单

| 文件 | 原因 | 内容 |
|------|------|------|
| patches/0001-makefile-ar-variable.patch | 上游静态库规则写死 `ar`，OHOS 工具链下归档器可能是 `llvm-ar`；改为 `$(AR)` 变量（默认 `ar`，配方可覆盖） | portability，无平台宏 |

## 五、test_package 设计（R34 合规）

`test_equihash.c` 用小参数（N=24/K=3，求解毫秒级）真实调用全部三个公开 API，共 4 项断言：

1. `solsize(24,3) == 11`（公式值，验证头文件与库一致）
2. `solve()` 对固定种子返回 1（真实 PoW 求解）
3. `verify()` 接受合法解（返回 1）
4. `verify()` 拒绝末字节篡改后的解（返回 0，正反向验证）

编译用 C++ 驱动（静态库内含 C++ 对象；`equihash.h` 无 `extern "C"` 守卫，
测试侧自行包裹，属测试写法不改上游）。`test()` 以 shell 重定向捕获日志，
解析 `RESULT: N passed, M failed` 行后输出 `HMBS_TEST_PACKAGE_RESULT`，
并同步输出 `HMBS_UPSTREAM_TEST_RESULT`（no_tests，审计见 MANIFEST）。

## 六、验证命令（真机待执行）

```bash
conan create archives/l/libequihash/1.0.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

预期：`make` 构建两个库目标成功；`test_equihash` 4/4 通过；
日志含 `HMBS_TEST_PACKAGE_RESULT`（discovered=4/passedCount=4）与
`HMBS_UPSTREAM_TEST_RESULT`（status=no_tests）两行标记。

## 七、已知限制

- CLI（`equihash`/`ehwait`/`ehpuzzle`）与 Python 绑定不在本包交付范围；
  如需工具形态可后续单独立项。
- 零外部依赖（L0i/R36 无需校验依赖发布；test_package 仅链 `-lequihash`）。
