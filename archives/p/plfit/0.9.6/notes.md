# plfit 0.9.6 适配笔记

## 编译环境
- 构建系统: cmake（CMake 4.4.3；上游要求 ≥3.12）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，sysroot aarch64-linux-ohos）
- 目标平台: HarmonyOS PC (aarch64)，conan profile ohos-aarch64
- 状态: built

## 上游测试清点（R51 申报表）
| 项 | 值 |
|---|---|
| test/ 源文件 | 10 个 .c（含 test_common.c）+ 1 个 Python 模块测试 |
| CTest 注册数（ctest -N） | 9 |
| 实际执行 | 9 |
| 通过 | 9/9（100%） |
| 数据文件 | data/*.dat，测试经 DATADIR 宏指向源码树 data/ |
| 已排除 | test_python_module.py（SWIG Python 绑定；本配方 PLFIT_COMPILE_PYTHON_MODULE=OFF 不构建） |

## 编译步骤
1. init-build 下载官方源码 tag 归档 `plfit-0.9.6.tar.gz`（sha256 b44e592c1b96abff1255a4d67bee52cfe2a6414f975fb42fc3ffd2547bc8a535）
2. 施加补丁 0001（libm NOTFOUND 空置）+ 0002（静态归档安装）
3. `conan create -pr:h=ohos-aarch64` → CMake configure → `make -j1`
4. `ctest --output-on-failure`：9/9 通过（在 conan create 内执行，R51）
5. `cmake.install` 产物：`lib/libplfit.a`、`include/plfit/*.h`、`lib/pkgconfig/libplfit.pc`、`bin/plfit`、`bin/plgen`
6. test_package：C 消费者测试（11 项检查）+ CLI 冒烟 `test.sh`（8 项检查）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 成功但链接失败：`ld.lld: error: unable to find library -lMATH_LIBRARY-NOTFOUND` | OHOS sysroot 不含独立 libm.so（数学函数由 libc 提供），且 CMake 不识别 HarmonyOS 平台，`FIND_LIBRARY(MATH_LIBRARY NAMES m)` 返回 NOTFOUND 并被原样传入所有 link 行 | 补丁 0001：`if(NOT MATH_LIBRARY) set(MATH_LIBRARY "")`（zxcvbn-c 2.6 同款先例）。实测 clang 本身接受 `-lm`（LM-OK），但 CMake 层面发现不了文件，空置最稳 |
| 2 | 静态构建 `make install` 后只有 bin/include/pkgconfig，无 `libplfit.a` | 上游 `install(TARGETS plfit LIBRARY ...)` 未声明 ARCHIVE artifact kind，静态库不属于 LIBRARY | 补丁 0002：追加 `ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}` |
| 3 | （预防）并行 make 在 HMDFS 上 jobserver fifo 报 EPERM | E074（设备文件系统限制） | conanfile.py `cmake.build(build_tool_args=["-j1"])` |

## 源码修改
- `patches/0001-CMakeLists.txt.patch`：顶层 CMakeLists.txt，libm NOTFOUND 空置（+5 行；无平台宏，通用可移植语义）
- `patches/0002-src-CMakeLists.txt.patch`：src/CMakeLists.txt，`install(TARGETS plfit ...)` 追加 ARCHIVE 安装（+3/-1 行）

## 依赖版本
无第三方依赖（仅 C 运行库；数学函数由 OHOS libc 提供）

## 验证结果
```bash
# 上游 CTest（设备原生，与 conan create 同路径）
100% tests passed, 0 tests failed out of 9

# CLI 冒烟
./plfit -b data/karate.dat       -> "D 2.16147 2 -72.259 ..."
plgen -s 42 2000 2.5 | ./plfit -b -> alpha ≈ 2.5
```

## 注意事项
- OHOS 无独立 libm：下游不要依赖 `-lm`（package_info 不声明 system_libs=m）
- 默认 `shared=False`（静态）；动态构建可 `-o shared=True`（上游 LIBRARY 安装规则本身支持）
- 精确 p 值（`-p exact`）会做约 2500 次重采样，耗时较长；测试与冒烟均使用默认 SKIP

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libplfit.a | ~250 KB | 静态库 |
| bin/plfit | ~30 KB | 幂律拟合 CLI |
| bin/plgen | ~30 KB | 幂律样本生成 CLI |
| include/plfit/*.h | — | 5 个公共头文件 |

**编译结束**: 2026-09-17
