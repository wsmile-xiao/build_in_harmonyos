# volk 3.3.0 适配笔记（GNU Radio VOLK · HarmonyOS PC）

## 基本信息

- 上游仓库：`https://github.com/gnuradio/volk`（GNU Radio VOLK，LGPL-3.0-or-later）
- 上游版本：`3.3.0`
- 源码归档：`https://github.com/gnuradio/volk/releases/download/v3.3.0/volk-3.3.0.tar.gz`
- SHA-256：`89d11c8c8d4213b1b780354cfdbda1fed0c0b65c82847e710638eb3e21418628`
- 任务基线：`c611f7d61b`（branch `feat/volk-3.3.0`）
- 构建系统：CMake（Conan `CMakeToolchain` + `CMakeDeps` + Ninja/Make）
- 包类型：shared library（上游 `add_library(volk SHARED ...)`，3.3.0 无 static 目标）
- 状态: built

> 说明：本目录是 GNU Radio VOLK。软件目录下的 `1.4.350/` 是同名但无关的
> `zeux/volk`（Vulkan Overlay Loader）历史归档，二者不是同一上游，本次未改动。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| fmt | 11.1.3 | `volk_profile`/`volk_test_all` 链接 fmt。上游 FetchContent 钉 10.2.1，制品仓无；11.1.3 为最接近的已发布 OHOS 二进制 |
| Python mako | 1.4.3 | 上游构建期模板引擎（`volk_python_check_module`），recipe `build()` 内确定性安装 |
| orc | — | **关闭**：`FindORC` 需要 `orcc` 工具，制品仓 `orc/0.4.42` 关闭 tools 未提供，`ORC_FOUND` 必然为假 |
| cpu_features | 内置 | 源码包内含子模块内容，`find_package(CpuFeatures QUIET)` 失败后走 `add_subdirectory`（recipe 必须让 `CMAKE_SYSTEM_PROCESSOR=aarch64`，否则整个 cpu_features 分支被跳过） |

## 构建步骤（探索 → 配方）

```bash
# 探索（裸 cmake + OHOS SDK toolchain）
cmake -G Ninja -B build-ohos -S . \
  -DCMAKE_TOOLCHAIN_FILE=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib \
  -DCMAKE_CXX_FLAGS=-DFMT_DEPRECATED_HEAVY_CORE \
  -Dfmt_DIR=<conan CMakeDeps 目录> -DENABLE_ORC=OFF -DENABLE_TESTING=ON
cmake --build build-ohos -j4 && cmake --install build-ohos
# 上游测试（先按 E077 重签 ELF，再跑 ctest）
ctest --output-on-failure -j2     # 154/154 通过，66.2s

# 配方（Conan，G2 干净构建等同此命令）
conan create archives/v/volk/3.3.0 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

recipe 关键行为：

- `generate()`：`CMakeDeps` 显式生成（否则 `find_package(fmt)` 落空 →
  FetchContent 拉 fmt 10.2.1 并把它装进本包，见问题 #7）；os=OHOS 时固定
  `CMAKE_SYSTEM_NAME=OHOS`、`CMAKE_SYSTEM_PROCESSOR=aarch64`（见问题 #8）；
  `ENABLE_ORC=OFF`、`ENABLE_TESTING=ON`、`ENABLE_MODTOOL=ON`、
  `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`、`-DFMT_DEPRECATED_HEAVY_CORE`。
- `build()`：确保 mako → configure/build → 按 E077 重签构建树 ELF →
  运行上游 ctest（154 用例）。
- `package()`：install + 拷贝 COPYING + `volk.pc` 改 `${pcfiledir}` +
  对 `bin/`、`lib/` 重签 ELF（先副本签名，失败不破坏原文件）。

## 问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 裸 cmake 构建静态归档目标 `rc=127`：`llvm-ranlib: inaccessible or not found` | OHOS SDK 只提供 `llvm-ar`，`<sdk>/llvm/bin/llvm-ranlib` 不存在；`ohos.toolchain.cmake` 无条件把 `CMAKE_RANLIB` 指到该路径 | 显式 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（该名是 `llvm-ar` 的符号链接） |
| 2 | `qa_utils.cc` 编译失败：`no member named 'format' in namespace 'fmt'` | 上游 FetchContent 钉 fmt 10.2.1；自 fmt 11 起 `<fmt/core.h>` 不再包含 `fmt/format.h`，而 `qa_utils.cc` 只 include `<fmt/core.h>` | 使用 fmt 官方兼容开关 `-DFMT_DEPRECATED_HEAVY_CORE`（`tc.extra_cxxflags`），不改上游源码、0 补丁 |
| 3 | ORC 探测失败 | 制品仓 orc/0.4.42 关闭 tools，无 `orcc` 可执行文件，`FindORC` 的 `find_package_handle_standard_args(... ORCC_EXECUTABLE)` 必然失败 | 显式 `ENABLE_ORC=OFF` |
| 4 | 安装后的 `volk-config-info` 执行报 `Operation not permitted` | CMake install 期改写 RPATH（删除构建树 RUNPATH）→ 改动 ELF → 链接期 `.codesign` 失效（E077） | `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` 避免改写；并设 `CMAKE_INSTALL_RPATH=$ORIGIN/../lib` 使 `bin/` 工具免 LD_LIBRARY_PATH 即可加载 libvolk（CI L2 smoke），`package()` 仍按 E077 四步流程重签 |
| 5 | `volk.pc` 内嵌绝对安装前缀 | 上游模板直接把 `CMAKE_INSTALL_PREFIX` 写入 prefix/libdir/includedir | `package()` 改写为 `${pcfiledir}/../..` 相对路径 |
| 6 | 构建期缺 mako（干净 CI 环境） | mako 非系统包，属 Python 模块 | `build()` 先探测 import，缺失则 `python3 -m pip install 'mako>=0.4.2'`（mesa/acme-tiny 先例） |
| 7 | `find_package(fmt)` 未命中 → FetchContent 拉取 fmt 10.2.1 并以子项目安装进本包（`lib/libfmt.a`、`include/fmt/*`） | 配方 `generate()` 只生成了 `CMakeToolchain`，没有生成 `CMakeDeps`（test_package 有用 `generators="CMakeDeps"` 才正常） | `generate()` 中显式 `CMakeDeps(self).generate()`；复验后包内无 fmt 泄漏 |
| 8 | Conan 构建的 `libvolk.so` 无 SONAME/版本链（只有裸 `libvolk.so`），且日志出现 `Building Volk without cpu_features` | 构建宿主系统是 HarmonyOS：Conan 工具链不设目标系统 → CMake 采用宿主 `CMAKE_SYSTEM_NAME=HarmonyOS`（无平台模块）→ `CMAKE_SYSTEM_PROCESSOR=unknown`，上游按处理器开关 CPU_FEATURES 的分支被跳过、共享库 SONAME 规则缺失 | recipe `generate()` 中 os==OHOS 时 `CMAKE_SYSTEM_NAME=OHOS` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（fmt/brotli/glfw 同款），对齐 CMake 自带 `Modules/Platform/OHOS.cmake`；复验后 SONAME 链恢复且 cpu_features 编译 |
| 9 | CI（PR #13445 / build #63475）`conan-build-test` 失败：`ConanException: Python mako is required to build VOLK but not importable after install`（本地 W3 通过） | CI worker 上 **Conan 进程自身的 Python 与 build 环境 Python 不是同一个解释器**：`pip install --user` 由 conanbuild 环境的 `python3` 执行（装进该解释器的 user site），而旧实现用 Conan 进程内的 `importlib.metadata.version("mako")` 复检，二者 user site 不同 → 复检必然失败 | `_ensure_mako()` 改为**统一在 conanbuild 环境内探测/安装/复检**（`self.run('python3 -c "import mako"', env="conanbuild")`），与 CMake `find_package(PythonInterp 3)` 实际使用的解释器一致，消除解释器错配 |
| 10 | CI L0k (R38) 把本包误判为纯库（warn：commands.json exists but package looks like a library） | `detect_bindirs.py` 只认静态非空 `cpp_info.bindirs` 声明；本包 bin/ 产物真实存在（conan-create.log 安装/签名记录 + W3 L1e 移走 bin/ 后测试失败），但配方未显式声明 bindirs | `package_info()` 显式 `self.cpp_info.bindirs = ["bin"]`（审计 P3-1 建议；kcoreaddons5 先例），无功能副作用 |

## 源码修改

无源码修改，`patches_applied: []`。全部适配通过 CMake 变量、fmt 官方兼容宏
与 recipe 的 `package()` 处理完成。

## 上游测试（R51）

- `ctest -N` 清点：**154** 个用例（`qa_volk_*`，`lib/CMakeLists.txt` 对每个
  kernel 注册，`volk_test_all` 比较 generic/neon/neonv8 实现）。
- 实跑（conan create 的 `build()` 内）：`ctest --output-on-failure -j2` →
  **154/154 通过**，`100% tests passed, 0 tests failed out of 154`。
- 探索阶段裸 cmake 构建同套件亦 154/154（66.2s，设备现场执行）。
- `tests/` 子目录的 GoogleTest 套件需要 GTest（制品仓未提供）默认跳过，
  与上游行为一致（`if(NOT fmt_FOUND OR NOT GTest_FOUND) return()`）。

## 产物边界

- `lib/libvolk.so.3.3.0`（SONAME `libvolk.so.3.3`；DT_NEEDED 仅 `libc.so`，无 Conan cache 绝对路径泄漏，E537 复验通过）
- `bin/` 工具带相对 RPATH `$ORIGIN/../lib`，安装后可直接运行
  `volk-config-info --version`（无需 LD_LIBRARY_PATH）
- 173 个公共头（含生成的 `volk.h` 与 `kernels/volk/*.h`）
- `lib/cmake/volk`（`Volk::volk`）与可重定位 `lib/pkgconfig/volk.pc`
- 可执行文件：`bin/volk-config-info`、`bin/volk_profile`、`bin/volk_modtool`
- Python 包：`lib/python3.12/site-packages/volk_modtool/`
- `licenses/COPYING`（LGPL-3.0-or-later）
- 不提供静态库；不捆绑 fmt（依赖走制品仓 fmt/11.1.3）

## Conan/W3 验证

- `ohc-run.py conan-verify volk 3.3.0`：**PASS**（G0/G1/G2/G3/G4；日志
  `reports/conan-create.log`，报告 `reports/conan-verify-report.md`）。
- 框架对 `volk/3.3.0@ohpcd/stable` 无法回解析 package ID，L2/L4/L5 被 skip；
  已按实际 package 路径做等价人工核验并留证：`reports/conan-verify-supplement.md`
  （G4 产物 194 文件、L2 消费者实跑 7/7 + codesign、L4 PIE/NX/RELRO/BIND_NOW、
  L5 首个本地包 SHA256 基线、E537 复验）。
- test_package（R34/R53）：`test.c` 真实调用 `volk_get_machine()/`
  `volk_get_alignment()/volk_malloc()/volk_32f_s32f_multiply_32f()` + 版本宏，
  7 项断言全过；鸿蒙特有断言 `llvm-readelf -S libvolk.so.3.3.0 | grep codesign`
  实际执行通过。
---

**编译结束**: 2026-09-28 12:02
**最终状态**: built
