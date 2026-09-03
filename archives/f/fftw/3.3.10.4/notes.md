# fftw 3.3.10 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出动态 libfftw3.so + libfftw3_threads.so，供 dlopen 及作依赖。

## 关键适配

### 二进制签名（从 3.3.10.2 移植）
- **`_sign_binaries()` 方法**：OHOS 平台要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied。
- 使用 `/data/service/hnp/bin/llvm-objcopy` 和 `/data/service/hnp/bin/binary-sign-tool`。
- 签名是内容哈希（存 .codesign 节），链接之后再改字节就失效。
- 守卫 `if self.settings.os != "OHOS": return` — 在 Linux profile 上工具不存在。

### 线程支持（从 3.3.10.2 对齐）
- **`--enable-threads`**：产出独立的 `libfftw3_threads.so`（默认不加 `--with-combined-threads`，与 3.3.10.2 的 `WITH_COMBINED_THREADS=OFF` 对齐）。
- pyfftw 按 `-lfftw3_threads` 探测多线程支持，折进主库就探测不到。
- `package_info()` 更新为 `libs = ['fftw3', 'fftw3_threads']`。

### 不开 OpenMP
- autotools 默认不启用 OpenMP（与 3.3.10.2 的 `ENABLE_OPENMP=OFF` 对齐）。
- 设备实测：SDK 里的 libomp.so 产物 RUNPATH 被烤成带 SDK 版本号的绝对路径，换机器就炸。
- pyfftw 的 setup.py 自带逃生口：定义 `PYFFTW_USE_PTHREADS` 即优先走 pthreads。

### 系统识别
- `--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`（build == host 走原生路径，直接跳过 config.guess，无需打补丁）。
- conandata.yml 的 `patches: {}` — 不使用 config.guess/config.sub 补丁。

### 包信息
- `pkg_config_name` 显式设为 `"fftw3"`（与 3.3.10.2 对齐）。
- `cmake_file_name` = `"fftw"`，`cmake_target_name` = `"fftw::fftw"`。
- `system_libs` = `['m']`（os in ("Linux", "OHOS")）。

### include 目录检测（从 3.3.10.2 移植）
- `_detect_include_dirs()` 方法：扫 include/ 下含头文件的子目录，避开与标准头同名的子目录。
- 防止 fmt/locale.h 之类遮蔽系统头的 -isystem 污染问题。

## 版本对比

| 特性 | 3.3.10 (autotools, 改进后) | 3.3.10.2 (CMake) |
|------|---------------------------|-------------------|
| 构建系统 | autotools | CMake |
| 二进制签名 | ✅ `_sign_binaries()` | ✅ `_sign_binaries()` |
| 线程支持 | ✅ `--enable-threads` | ✅ `ENABLE_THREADS=ON` |
| 独立线程库 | ✅ (不加 --with-combined-threads) | ✅ `WITH_COMBINED_THREADS=OFF` |
| OpenMP | ❌ (默认关闭) | ❌ `ENABLE_OPENMP=OFF` |
| 单精度 | ❌ (默认不建) | ❌ `ENABLE_FLOAT=OFF` |
| 长双精度 | ❌ (默认不建) | ❌ `ENABLE_LONG_DOUBLE=OFF` |
| SONAME 修复 | N/A (autotools libtool 正确) | ✅ 补丁修正写反的 SOVERSION/VERSION |
| pkg_config_name | ✅ 显式 "fftw3" | ✅ 显式 "fftw3" |
| include 检测 | ✅ `_detect_include_dirs()` | ✅ `_detect_include_dirs()` |

## 状态
built（CI conan create + test 通过）

---

## 附：与本目录 patches/ 的关系

`patches/0001-config.guess.patch` 与 `0002-config.sub.patch` 是**早期源码构建**时期的产物
（给 config.guess/config.sub 加 HarmonyOS 识别分支）。

**本 conan 配方不使用它们**（`conandata.yml` 的 `patches: {}`）——改为在 configure 时显式给出
`--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`，
`build == host` 让 configure 走原生路径、**直接跳过 config.guess**，无需打补丁。
补丁文件保留作为历史记录，供仍走源码构建路线的人参考。

<details>
<summary>早期源码构建记录（存档）</summary>

# fftw 3.3.10 适配笔记

## 编译环境
- 构建系统: cmake（autotools 失败后改用）
- 编译日期: 2026-04-26
- 编译器: clang/clang++
- 状态: partial（CMake 编译成功）

## 编译步骤
1. 下载源码 `http://www.fftw.org/fftw-3.3.10.tar.gz`
2. 更新 config.guess 和 config.sub 为最新版本
3. **Autotools 构建失败**，改用 CMake
4. CMake 配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..`
5. `make -j$(nproc)`
6. `make install`
7. 预编译包包含: libfftw3.so、头文件、pkg-config 文件、cmake 配置文件

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Autotools configure 失败 | config.guess/config.sub 无法识别 OHOS | 更新 config.guess/config.sub 补丁 |
| 2 | Autotools 仍然失败 | 即使更新后仍有兼容性问题 | 改用 CMake 构建 |
| 3 | CMake policy 警告 | CMake 版本策略不兼容 | 设置 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| config.guess | 添加 OHOS 平台识别 | ✅ 0001-config.guess.patch |
| config.sub | 添加 OHOS 平台支持 | ✅ 0002-config.sub.patch |

## 依赖版本
无外部依赖

## 注意事项
- Autotools 构建失败，必须使用 CMake
- 需要设置 CMAKE_POLICY_VERSION_MINIMUM=3.5

</details>
---

**编译结束**: 2026-09-04 03:04
**最终状态**: built
