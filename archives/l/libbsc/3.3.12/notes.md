# libbsc 3.3.12 — 适配笔记

> 档案创建时间: 2026-09-17
> 最后更新: 2026-09-17
> 状态: built

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libbsc（块排序数据压缩库 + bsc CLI） |
| 版本 | 3.3.12（2025-09-09 发布） |
| 许可证 | Apache-2.0 |
| 构建系统 | CMake ≥ 3.24 |
| 源码 | https://github.com/IlyaGrebnov/libbsc/releases/download/3.3.12/libbsc-3.3.12.tar.gz |
| sha256 | 3d8eee9351468bdd3fb3bc28dda0e24cfc0332997eb0210ea7bd548d77c3d194（与 Homebrew/Nix 一致） |

## 二、适配决策（路径 A：纯配方适配，无源码补丁）

### 决策 1: ARM64 支持确认，无需补丁
- `libbsc/platform/platform.h` 将 `__aarch64__` 映射到 `LIBBSC_CPU_FEATURE_A64`
- adler32/qlfc 有 A64 NEON intrinsic 分支（`#elif LIBBSC_CPU_FEATURE == A64`）
- x86 cpuid/xgetbv 内联 asm 由 `#if LIBBSC_CPU_FEATURE >= SSE2` 守卫（A64=1 < SSE2=2），AArch64 下完全编译排除，无 x86 泄漏
- `bsc_get_cpu_features()` 在 A64 下返回编译期常量，无运行时架构探测

### 决策 2: BSC_ENABLE_NATIVE_COMPILATION=OFF（E100）
- 禁用 `-march=native`，避免构建机 CPU 特定指令进入其他 OHOS 设备
- Homebrew/Nix 同样默认禁用，与主流打包实践一致

### 决策 3: BSC_ENABLE_OPENMP=OFF
- OHOS SDK（ohos-sdk_26.0.0.18）native/llvm/lib 无 libomp，/system 无 libomp*
- 单线程模式已在 HarmonyOS aarch64 设备实测 round-trip 通过
- 保留 openmp option（默认 False），若未来 SDK 带编译器 runtime 可开启

### 决策 4: DT_SONAME 经工具链变量注入（E322/libharu 模式）
- 上游 CMakeLists.txt 的 libbsc 目标无 SOVERSION，且 CMake 无 Platform/HarmonyOS.cmake，SONAME 链接标志为空
- 配方 generate() 中设置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG="-Wl,-soname,"`，实测产生 `DT_SONAME libbsc.so`
- 已在本机构建验证：readelf -d 显示 `(SONAME) Library soname: [libbsc.so]`

### 决策 5: 上游无测试 → no_official_test 白名单
- 上游无 enable_testing/add_test、无 tests/ 目录、无 benchmark/example 目标
- 上游 README 的官方验证方式 = 手工 CLI round-trip
- 已在 ci/config/no_official_test.txt 追加 libbsc 条目（附完整依据）
- 我们用 test_package 完全覆盖：库 API round-trip + CLI round-trip + OHOS 专项

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| (无) | 上游原生支持 AArch64 | 无需修改 | 无补丁 |

## 四、编译命令
```bash
# 探索性编译（本机 HarmonyOS aarch64）
cmake -S ~/builds/libbsc/libbsc-3.3.12 -B build -DCMAKE_BUILD_TYPE=Release \
  -DBSC_ENABLE_NATIVE_COMPILATION=OFF -DBSC_ENABLE_OPENMP=OFF -DBSC_ENABLE_CUDA=OFF \
  -DBSC_BUILD_SHARED_LIB=ON
cmake --build build -j
readelf -d build/libbsc.so | grep SONAME   # -> libbsc.so

# Conan 验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libbsc 3.3.12
```

## 五、产物
- lib/libbsc.so（shared，DT_SONAME=libbsc.so）
- include/libbsc/{libbsc.h, filters.h}
- bin/bsc（CLI，动态链接 libbsc.so）

## 六、结束记录
- **最终状态**: built（本机实测通过：CLI round-trip、单线程 round-trip、shared 构建 + SONAME）
- **结束时间**: 2026-09-17
