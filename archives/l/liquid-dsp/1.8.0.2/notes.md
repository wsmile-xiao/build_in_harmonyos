# liquid-dsp 1.8.0.2 适配笔记

## 任务身份

- 目标库: `liquid-dsp`（上游版本 v1.8.0）
- 版本号: `1.8.0.2`（R37：同上游版本再次适配修复 → 递增后缀；1.8.0 已 published、1.8.0.1 已 built）
- 分支: `feat/liquid-dsp-1.8.0.2`
- 官方源码: `https://github.com/jgaeddert/liquid-dsp/archive/refs/tags/v1.8.0.tar.gz`
- 源码 SHA-256: `abef8b2ddfd58c0a84ecda4f62158c4824b916144af4a2b07776e1a144d8cda4`（本地实测一致）

## W0 依赖核验

上游 CMake 将 FFTW 设为可选（`FIND_FFTW`），核心库仅链接平台 C/math 运行库。
配方关闭 `FIND_FFTW`、examples、benchmarks 与 shared 输出，因此
**声明的 Conan 依赖闭包为空**，不存在需要 `conan download` 校验的强制第三方依赖。

```text
$ python3 ohc-run.py init-build liquid-dsp 1.8.0 --url=... --auto
  ✅   所有依赖已就绪
```

## 上游测试入口清点（R51 步骤一）

| 入口 | 位置 | 数量 |
|---|---|---|
| CTest 注册 | `CMakeLists.txt:104 enable_testing()` / `:889 add_test(NAME autotest COMMAND xautotest)` | 1 个聚合 target |
| 聚合程序 | `autotest/xautotest.c` → 链接 `libliquid_autotest` | — |
| 用例注册表 | `autotest/liquid_autotest_registry.h`（extern 声明 1341 / 数组条目 1341） | **1341** |
| 用例源文件 | `src/**/tests/*_autotest.c` | 161 |

## 构建与平台定位

```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLES=OFF -DBUILD_AUTOTESTS=ON \
         -DBUILD_BENCHMARKS=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON \
         -DFIND_FFTW=OFF -DCMAKE_INSTALL_PREFIX=<prefix>
make -j20 && make install
```

平台探测结果（OHOS aarch64 真机，clang 15.0.4）：

```text
NEON    : Yes, flags=' '      (aarch64 自动启用)
SSE/AVX/AVX512/AltiVec : No
Threads : Yes
FFTW    : No                  (使用内置 FFT)
```

**首个错误 / 根因 / 修复**

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | `conan create -pr=default` 报 `Invalid: 'settings.os.version' value not defined` (exit 6) | `default` profile 只有 `os=OHOS`，缺 `os.version`；OHOS 适配版 conan 要求该字段 | 改用 CI 同款 `ci/conan/profiles/ohos-aarch64`（`os.version=6.0`、`libcxx=libc++`、`cppstd=17`），`-pr:h`/`-pr:b` 同时指定 |
| 2 | 静态安装后 `find_package(liquid)` 失败 | 上游 static-only 构建重命名 `LIBNAME`，Config 与 Targets 文件名不一致 | `patches/0001-cmakelists-static-config.patch` 保持逻辑包名 `liquid`（沿用 1.8.0.1 已验证补丁） |
| 3 | make 阶段 `jobserver mkfifo: ... Operation not permitted` | OHOS/HMDFS 下 make jobserver FIFO 受限，**非致命环境告警** | 不处理；构建与测试均正常完成 |

## 上游测试实测（R51 步骤二）

配方已集成：`BUILD_AUTOTESTS=ON`，`build()` 调用 `cmake.test()`。

```text
$ ctest --output-on-failure          # conan create 内部
    Start 1: autotest
1/1 Test #1: autotest .................   Passed  140.56 sec
100% tests passed, 0 tests failed out of 1
```

聚合程序 `xautotest` 内部的用例统计（独立真机运行）：

```text
tests  : pass=1341   fail=0   skip=0
checks : pass=716520 fail=0
overall: warn=55     PASS
```

- 用例覆盖率：**1341/1341（100%）**，无裁剪、无修改、无漏测
- 断言：716520/716520（100%）
- 用例名清单：`reports/upstream-test-names.txt`（1341 行）
- 原始日志：见 `reports/test-report.md` 的日志清单

## test_package

消费者通过 `find_package(liquid CONFIG REQUIRED)` 链接 `liquid::liquid-static`，真机执行 **6/6**：

| 用例 | 说明 |
|---|---|
| generic-1 | `liquid_nchoosek(5,2) == 10.0f` |
| generic-2 | `liquid_version` 非空 |
| generic-3 | `windowf_create/push/index/destroy` 行为正确 |
| **`[OHOS-1]`** | 目标平台标识：`__OHOS__` 已定义（OpenHarmony 构建） |
| **`[OHOS-2]`** | aarch64 NEON 加速路径：`dotprod_rrrf` 数值正确（`__ARM_NEON` 已启用） |
| **`[OHOS-3]`** | 内置 FFT 自包含：`FIND_FFTW=OFF` 下 DC/bin1 数值正确 |

**鸿蒙特有测试用例 = 3（≥1）**。

## 源码修改

无源码改动。仅应用 `patches/0001-cmakelists-static-config.patch`
（CMake 包导出身份一致性，不触碰 DSP 源码与上游测试）。

## 验证结果

```text
conan create liquid-dsp/1.8.0.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...
  → exit 0, 240s, Package '4b977264131a1c74e82bd6bb51b63cc9aadc4cfa' created
  → 上游 CTest 1/1 Passed (140.56s)
  → test_package 6/6 ALL PASS
```

## 注意事项

- 静态库制品为 `lib/libliquid.a`，CMake 导出目标 `liquid::liquid-static`，pkg-config 名 `liquid-dsp`。
- `liquid_version` 字符串来自上游 `include/liquid.h`，v1.8.0 报告 `1.8.0`（与上游 tag 一致）。
- 复现必须使用 `ci/conan/profiles/ohos-aarch64`；`default` profile 缺 `os.version` 会直接 Invalid。

## 知识沉淀

- `E327`：static-only 构建中 target/制品变体不得改变 Config/Targets/install export 的逻辑包身份。
- `DRAFT-liquid-dsp-1.8.0.2-ohos-conan-default-profile-missing-os-version`：
  OHOS 适配版 conan 下 `default` profile 缺 `os.version` 会让 `conan create` 在
  package_id 计算阶段直接 Invalid（exit 6）；本地验证必须使用 CI 同源
  `ci/conan/profiles/ohos-aarch64`。

## 结束标记

最终状态: built
---

**编译结束**: 2026-09-25 17:08
**最终状态**: built
