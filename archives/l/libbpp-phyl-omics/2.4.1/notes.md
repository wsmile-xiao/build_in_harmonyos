# libbpp-phyl-omics 2.4.1 适配笔记

## 编译环境
- 构建系统：cmake；编译器 clang/clang++ 15.0.4
- 状态：built（真机预检后由 HMBS 提交）
- 上游：https://github.com/BioPP/bpp-phyl-omics ，tag v2.4.1
  （sha256 fb0908422e59c71065db874e68d5c71acddf66d8a51776f7e04a5f8d5f0f6577）
- 依赖：libbpp-seq-omics/2.4.1、libbpp-seq/2.4.1（Conan，已发布）；libbpp-phyl/2.4.1（**源码 vendor**，未发布到 ohpcd）

## 与同族的关系

Bio++ 家族 `bpp-core → bpp-seq → (bpp-seq-omics | bpp-phyl) → bpp-phyl-omics` 链上
的系统发育-组学一环。配方骨架复用同族先例 `libbpp-seq-omics`（含 E543 的
CMAKE_<LANG>_COMPILER_TARGET 交叉目标注入、依赖 CMake 导出 shim），并进一步泛化为
**多依赖 shim**：对 Conan 依赖 libbpp-seq-omics / libbpp-seq 分别做 shim，统一注入
bpp-seq-omics / bpp-seq / bpp-core 三个 `_DIR`。

## 依赖发布检查与 libbpp-phyl 的 vendor（W0/R36）

- libbpp-seq-omics/2.4.1：已发布（archives/l/libbpp-seq-omics）
- libbpp-seq/2.4.1：已发布（archives/l/libbpp-seq，包内合并 bpp-core）
- **libbpp-phyl/2.4.1：未发布到 ohpcd/任何 remote**。真机预检 conan create 在依赖图
  解析阶段报 `Package 'libbpp-phyl/2.4.1' not resolved`（L0i/R36），先于编译失败。
  上游 bpp-phyl-omics 硬依赖 `find_package(bpp-phyl 12.0.0 REQUIRED)`，无法去除。
  按同族先例 **libbpp-seq vendor bpp-core** 的成熟做法，把 **libbpp-phyl 源码 vendor**
  进本配方（conandata.yml `bpp_phyl` 条目），在 `build()` 里用与主构建同源的
  conan_toolchain 先构建到私有前缀 `bpp-phyl-prefix`，phyl-omics 经 CMAKE_PREFIX_PATH
  找到它。vendored bpp-phyl 的 `find_package(bpp-seq 12.0.0 REQUIRED)` 由已发布的
  libbpp-seq/2.4.1 的 shim（注入 bpp-seq_DIR / bpp-core_DIR）满足。构建/打包后，
  vendored libbpp-phyl 的 .a 与 bpp-phyl-config.cmake 合并进 libbpp-phyl-omics 包
  （对齐 libbpp-seq 把 vendored bpp-core 并入自身的先例）。

## 上游测试清点（源码审计，tag v2.4.1）

**上游没有任何自动化测试**：v2.4.1 归档无 test/、tests/ 目录；顶层 CMakeLists.txt
仅 project/find_package/add_subdirectory(src)，无 enable_testing / add_test /
BUILD_TESTING / ctest；src/CMakeLists.txt 仅 add_library(static/shared) + install。
因此 `upstream_test_total=0`，test_package 阶段如实输出 `status=no_tests`、
discovered=0/executed=0（对齐 aribb24/osmctools 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 依赖图解析阶段报 `Package 'libbpp-phyl/2.4.1' not resolved`（先于编译失败） | libbpp-phyl/2.4.1 未发布到 ohpcd/任何 remote，但 phyl-omics 的 `find_package(bpp-phyl 12.0.0 REQUIRED)` 硬依赖它 | 从 requirements() 移除 libbpp-phyl，按同族先例 vendor 其源码（conandata.yml bpp_phyl），build() 里先构建到 bpp-phyl-prefix，phyl-omics 经 CMAKE_PREFIX_PATH 找到；vendored 产物并入本包 | 
| 2 | find_package(bpp-seq-omics/bpp-seq) 报 references ... shared .so 不存在 | 依赖包裁了 .so 但保留指向它的 CMake 导出 | 构建内 shim：对 Conan 依赖 libbpp-seq-omics / libbpp-seq 逐包复制、剔除 shared 目标、BPP_LIBS_SHARED 重定向 static（同 libbpp-seq-omics）；vendored bpp-phyl configure 注入 bpp-seq_DIR/bpp-core_DIR 指其 shim |
| 3 | CMakeDeps 生成的 libbpp-*.cmake 遮蔽上游 config | 包名前缀不同 | Conan 包名用 libbpp-phyl-omics 前缀，注入 <name>_DIR 指向上游 config |
| 4 | 交叉编译静默产出 x86-64 | 上游 set(CMAKE_CXX_FLAGS) 覆盖 --target（E543） | CMAKE_<LANG>_COMPILER_TARGET / CMAKE_SYSROOT 注入 |

## 验证结果

- 真机 HarmonyOS aarch64：由 HMBS 预检执行（conan create 真实构建 + test_package 5 项断言）
- 上游测试：无（no_tests，upstream_test_total=0）
- 新增测试：test_package 真实调用 CountClustersMafStatistics API（5 项断言）
