# indi-aok 2.0-20221222093242 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-01（2026-10-02 复跑 W3）
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，aarch64-linux-ohos，libc++）
- 宿主 cmake: 4.1.2
- 状态: built（W3 `conan create` 端到端 PASS：`checks=4 fails=0 skips=1`）

## 上游测试清点（R51）
- 驱动子目录 `indi-aok/` 仅含 `CMakeLists.txt`、`lx200aok.cpp`（1535 行）、`config.h.cmake`、`indi_aok.xml.cmake`、`README.md`、`CHANGELOG`、`LOGO.png`
- `indi-aok/CMakeLists.txt` 无 `enable_testing()`/`add_test()`，`indi-3rdparty` 全仓无该驱动测试用例
- 结论: **上游确无测试**（清点证据＝子目录文件清单 + CMakeLists 无 ctest 注册）
- 因此按 R51 补充鸿蒙独有消费者测试（`test_package/check_driver.py`，4 项断言，见下）

## 编译步骤
1. `conan install --requires=libindi/2.2.2.1 --requires=libnova/0.16`（预取依赖并生成 CMakeDeps/CMakeToolchain）
2. 配方 `generate()` 注入两个探测提示（不改源码）：
   - `INDI_ROOT=<libindi 包目录>`：仓库级 `cmake_modules/FindINDI.cmake` 用该变量定位
     `indiversion.h`/`libindidriver.so`/`libindilx200.so`（组件 driver + lx200）
   - `Nova_DIR=<构建目录>/nova`：该目录内由配方生成私有 `NovaConfig.cmake`
3. `cmake.configure(build_script_folder="indi-aok")` → `cmake.build()` → `cmake.install()`
4. 产物：`bin/indi_lx200aok`、`share/indi/indi_aok.xml`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(INDI)` 报 "Could not find INDI include directory" | 驱动不消费 conan 的 `libindi` config 包（CMakeDeps 生成的包名是 `libindi`，而 CMakeLists 请求的是 `INDI`），走的是仓库级 `FindINDI.cmake` 模块模式，需外部提示 | 配方注入 `INDI_ROOT=<libindi 包目录>`（本地实测：`Found INDI 2.2.2 (driver+lx200)`） |
| 2 | `find_package(Nova REQUIRED)` 失败："By not providing FindNova.cmake … Could not find NovaConfig.cmake" | v2.2.2 整仓 `cmake_modules/` 无 `FindNova.cmake`（旧 2.0 代曾有），libnova 包也不安装 `NovaConfig.cmake` | 配方在构建目录生成私有 `NovaConfig.cmake`：`NOVA_INCLUDE_DIR`/`NOVA_LIBRARIES` 全部取自 libnova 的 cpp_info（`libnova.a`），并用 `Nova_DIR` 指向该目录（R49，不注入共享前缀） |
| 3 | 2.0 代源码编译报 libindi 属性 API/`std::any` 错误 | 2.0 代 `lx200aok.cpp` 面向 libindi 1.9 时代 API，且仓库级 `CMakeCommon.cmake` 设 `CMAKE_CXX_STANDARD 14`；制品仓仅有 libindi 2.2.2.1 | 源码代次对齐 v2.2.2（同样声明驱动 `Version 2.0`），其 `CMakeCommon.cmake` 已为 C++17；R8 禁止改被编译源码，故对齐代次而非打补丁 |
| 4 | CMake 4.1.2 拒绝 `cmake_minimum_required(VERSION 3.0)` | 2.0 代脚本策略过旧（CMake 4 不再接受 <3.5） | v2.2.2 代已是 `VERSION 3.16`，问题随源码代次对齐消解，无需 `CMAKE_POLICY_VERSION_MINIMUM` 绕过 |
| 5 | 驱动 DT_NEEDED 缺 `libindiclient.so.2`，宿主加载器报 `Error relocating libindilx200.so.2: tty_write_string / INDI::Telescope…: symbol not found` | `indi-aok/CMakeLists.txt` 只请求 `driver`/`lx200` 两个 INDI 组件，于是 `libindidriver.so.2`/`libindilx200.so.2` 进 NEEDED，而它们从 `libindiclient` 引入的符号（如 `tty_write_string`）只在链接期经同级 `.so` 间接解析、**未被记入 DT_NEEDED** → 闭包不完整 | **补丁 `0001-indi-aok-CMakeLists-link-indi-client.patch`**：请求 `client` 组件（`find_package(INDI COMPONENTS driver client lx200 REQUIRED)`）使 `libindiclient` 显式入 NEEDED。只改构建脚本，未触碰被编译源码（R8）。复跑 W3：`DT_NEEDED closure complete: libindiclient.so.2, libindidriver.so.2, libindilx200.so.2` |
| 6 | 手工验证时驱动执行报 `Error loading shared library libindidriver.so.2: (needed by …)` | 本机 `/storage` 为 FUSE 挂载，OHOS 共享库经 musl `mmap(PROT_EXEC)` 打开被拒（同一文件 `cp` 到 tmp 后加载亦 `Permission denied`）；libindi 自身配方亦在其 test_package 用静态库链接以规避同一限制 | 判为**宿主平台限制**而非打包缺陷：test_package 对此类拒绝记 SKIP 并打印加载器原文，闭包完整性改由确定性静态审计（DT_NEEDED + 包内文件存在性）保证 |

## 源码修改

**补丁 1 个**（`patches/0001-indi-aok-CMakeLists-link-indi-client.patch`），只改构建脚本 `indi-aok/CMakeLists.txt` 一行：

```
-find_package(INDI COMPONENTS driver lx200 REQUIRED)
+find_package(INDI COMPONENTS driver client lx200 REQUIRED)
```

**被编译源码（`lx200aok.cpp`）与仓库级脚本（`FindINDI.cmake`/`CMakeCommon.cmake`）均未改动**（R8 合规，补丁不含任何平台宏）。
其余适配点全部在配方层解决：探测提示（`INDI_ROOT`）+ 构建目录内私有 `NovaConfig.cmake`。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libindi | 2.2.2.1 | 提供 `libindidriver.so.2` + `libindilx200.so.2` + `libindiclient.so.2`（组件 driver/lx200/client） |
| libnova | 0.16 | 静态库 `libnova.a`（天文计算） |
| libev / zlib / curl / libusb / fftw3 等 | 由 libindi 配方传递 | 由 Conan 解析，无需在本包声明 |

## 验证结果

手工全流程（本地，aarch64 OHOS）：

```bash
# 配置
cmake -S <src>/indi-aok -B build -DCMAKE_TOOLCHAIN_FILE=<conan>/conan_toolchain.cmake \
      -DINDI_ROOT=<libindi 包目录> -DNOVA_INCLUDE_DIR=<libnova>/include \
      -DNOVA_LIBRARIES=<libnova>/lib/libnova.a
# --> Found INDI: .../libindidriver.so;.../libindilx200.so (found version "2.2.2")
# --> Configuring done
# 编译
cmake --build build -j2      # rc=0
file build/indi_lx200aok     # ELF 64-bit LSB, ARM aarch64, dynamically linked, interpreter /lib/ld-musl-aarch64.so.1
ls -l build/indi_lx200aok    # 88576 字节
```

W3（`conan create`，含 test_package 消费者测试）实测输出：

```bash
[ok]   bin/indi_lx200aok: AArch64 ELF, 88576 bytes
[ok]   share/indi/indi_aok.xml: driver name + executable reference match the package
[ok]   DT_NEEDED closure complete: libindiclient.so.2, libindidriver.so.2, libindilx200.so.2 (all provided by the libindi package)
[skip] host loader refused the OHOS shared-object closure: Error loading shared library libindidriver.so.2: (needed by .../bin/indi_lx200aok)
checks=4 fails=0 skips=1
RESULT: PASS
# 反向验证：移除 bin/indi_lx200aok 后 RESULT: FAIL（驱动缺失即失败，满足 L1e 破坏性验证）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/indi_lx200aok | 88576 B | INDI 驱动可执行文件（被 INDI 主程序 dlopen） |
| share/indi/indi_aok.xml | ~330 B | 驱动描述（`<driver name="LX200 AOK">indi_lx200aok</driver>`，version 2.0） |

## 注意事项

- **运行期依赖闭包**：驱动是插件式可执行文件，`libindilx200.so` 自身不声明 `NEEDED libindidriver`，符号由后者提供；`libindiclient` 曾因 CMakeLists 只请求两个组件而漏记（见问题 5，已由补丁修复）。运行须在完整闭包环境（conan runenv）中进行。
- **宿主加载器限制**：本机 `/storage`（FUSE）下 musl 无法 `mmap(PROT_EXEC)` 打开 OHOS 共享库（`Permission denied`，`cp` 到 `$TMPDIR` 后亦然），libindi 配方亦用静态链接规避；故 test_package 对这类宿主拒绝记 SKIP，闭包完整性由静态 DT_NEEDED 审计确定性保证。
- **未签名 ELF 执行限制**：OHOS 加载器对未签名二进制可能拒绝执行；test_package 对这类平台限制同样记 SKIP，仅对打包缺陷（缺产物/缺 soname/绝对路径 NEEDED）判 FAIL。
- **libnova 为静态库**：`NOVA_LIBRARIES` 需给 `libnova.a` 绝对路径，避免误取共享库或系统同名库。
- **INDI 数据目录**：`INDI_DATA_DIR` 由 v2.2.2 CMakeLists 固定为 `${CMAKE_INSTALL_PREFIX}/share/indi`，随包安装，无需额外参数。
- **上游无测试**：见上方 R51 清点；鸿蒙独有测试位于 `test_package/`。
---

**编译结束**: 2026-10-02 10:19
**最终状态**: built
