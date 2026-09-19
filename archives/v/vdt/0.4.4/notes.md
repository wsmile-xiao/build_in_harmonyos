# vdt 0.4.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18, clang 15.0.4)
- 目标平台: HarmonyOS PC (aarch64, os=OHOS)
- 状态: built

## 编译步骤

```bash
# 真机（HarmonyOS aarch64）
eval "$($HOME/.harmonybrew/bin/brew shellenv)"
cd $HOME/work/psj
conan create archives/v/vdt/0.4.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# conan-create-RC=0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure 失败 "Compatibility with CMake < 3.5 has been removed" | vdt 声明 cmake_minimum_required 3.2，本机 CMake 4.x 不兼容 | 加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（conanfile 中 cache_variable 固化） |
| 2 | aarch64 上 `-msse` 是未知选项 | 上游默认 `SSE=ON`（x86 专属） | arch 守卫：armv8 时 `NEON=ON`、`SSE/AVX/AVX2/FMA=OFF` |
| 3 | `from conan import ConanException` 报 ImportError | Conan 2.x 里 `ConanException` 在 `conan.errors` | `from conan.errors import ConanException` |
| 4 | test_package `test()` 里 `/data/service/hnp/bin/bash: inaccessible or not found`（Error 127） | 0.4.6 模板把 `CONFIG_SHELL` 默认值写成 CI worker 专有路径，真机上不存在 | 两个探针都用 `-Wl,-rpath,<pkg>/lib` 链接且 conanrun 已带 LD_LIBRARY_PATH，直接 `self.run("./consumer_probe", env="conanrun")`，不依赖外部 bash |
| 5 | `get(self, **sources)` 对 codeload URL 报 BadZipFile | codeload URL 末段是 tag 名、无 `.tar.gz` 后缀 | `get(self, filename="vdt-0.4.4.tar.gz", **sources, strip_root=True)` |
| 6 | 相对误差断言对负参考值失效（AI 检视 Medium，0.4.6 模板同款） | `rel = fabs((got-want)/(want != 0 ? want : 1))` 分母用带符号 `want`：`want<0` 时 `rel` 变负，`rel > 1e-7` 恒 false，断言被静默绕过（`test_vdt_ohos.cpp` 的 `sinv` 对 `-0.3`/`-1.25` 两点形同虚设） | 分母改 `std::fabs(want)`，保证相对误差恒为非负；`consumer.cpp` 的 `check()` 同款修正 |

## 源码修改

无（vdt 上游源码零修改，无 patches；仅编写 conanfile.py/conandata.yml/test_package 适配配方）。

## 依赖版本

无强制第三方依赖（C++11 标准库 + CMake 3.2+ + Python 3 仅用于 configure 阶段签名代码生成）。

## 上游测试申报台账（全量枚举）

测试入口均来自官方 v0.4.4 源码，`progs/units/CMakeLists.txt` 在 `-DDIAG=ON` 时注册：

| 入口 | 类型 | 是否独立用例 | 运行结果 |
|------|------|-------------|----------|
| exp_test / log_test / sqrt_test / sin_test / cos_test / inv_test / tan_test / tanh_test / asin_test / acos_test / atan_test / atan2_test | 用户测试源（函数单元测试） | 是（12 个） | 全部 exit=0 通过 |
| fpDifferentBit / printInstSet / test_randomPool | 工具/诊断程序 | 否（工具，非断言测试） | exit=0 运行成功 |
| test_fcnResponse / test_fcnComparison / test_fcnPerformance | 诊断程序（读样本文件比对） | 否（诊断，非独立断言用例） | exit=0 运行成功 |
| vdtPerfBenchmark / vdtArithmBenchmark / vdtArithmComparison | 基准程序 | 否（benchmark，不计用例） | 编译成功，未计入通过率分母 |
| progs/testExp.py / vdtNumpyTime.py / vdtNumpytest.py / vdtCtypesTest.py | Python 包装测试脚本 | 否（依赖 numpy 绑定的辅助脚本） | 未实例化（需自建 vdtnpfun.so 包装模块，属 python 绑定辅助，非库主体测试） |
| src/testFatlib.cc | fatlib 内部试验源 | 否（未注册 CMake 目标） | 未实例化 |

- 取数命令（源码声明独立用例数）：`ls progs/units/*_test.cpp | wc -l` → 12
- 当前配置实际实例化：12（DIAG=ON 全部构建）
- 实际执行通过：12/12，通过率 100%
- 统计口径：全目录枚举（progs/units 18 个 .cpp + progs 3 个 benchmark + 4 个 py 脚本），独立用例按用户测试源判定

## 验证结果

```bash
# 上游单元测试 12/12 通过（DIAG=ON，progs/units/*_test.cpp，由 build() 内真实执行）
# vdt/0.4.4: 上游单元测试执行完成：12/12（exp_test, log_test, sqrt_test, sin_test,
#            cos_test, inv_test, tan_test, tanh_test, asin_test, acos_test, atan_test, atan2_test）
# 消费者验证 consumer_probe：vdt::fast_exp/fast_sin/fast_cos/fast_log/fast_isqrt
#            + expv/sinv 共 13 项断言全部 PASSED（最大相对偏差 1.634e-16）
# 鸿蒙专项测试 ohos_special_probe：kOnOhos=1 kNeonPath=1，expv/sinv 8 点对拍 + fast_exp PASSED
# 打包：15 个 .h（include/vdt/）+ libvdt.so；conan create 退出码 0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（OHOS profile、NEON、DIAG=ON 并在 build() 内运行 12 个上游单元测试） |
| conandata.yml | 官方源（codeload）+ sha256 |
| test_package/consumer.cpp | 消费者验证用例（13 项断言） |
| test_package/test_vdt_ohos.cpp | 鸿蒙专项测试用例 |
| manifest.yaml | 版本 manifest |

## 注意事项

- 本库为纯库（无 bin/），按 R38 不需要 commands.json。
- vdt 函数为快速近似实现，双精度对拍阈值 1e-7（上游自身也非逐位精确）。
- 上游测试枚举台账已按双口径记录：source_declared_total=12，executed_passed=12（100%）。
- 与 archives/v/vdt/0.4.6、archives/c/cern/0.4.6 的关系：0.4.6 是同一上游的另一 tag；
  本目录为任务 #11636 绑定的 v0.4.4。0.4.4 与 0.4.6 上游源码仅顶层 CMakeLists.txt
  一行之差（`VECT_OPT`：`-Ofast` → `-O3`），其余文件逐字节一致。
