# silo-llnl 4.12.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built（待真机 rule4 门禁验证）

## 编译步骤

Silo 4.12.1 已移除 autotools，纯 CMake 构建。conan 配方（conanfile.py）核心步骤：

1. `cmake.configure()`：写入下列关键 cache variables
   - `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 无 HarmonyOS 平台模块，别名 Linux 以启用 `if(UNIX)` 分支，与 airspy/atracdenc/hdf5 同款做法）
   - `SILO_ENABLE_HDF5=OFF`（见下方问题 #1：真机 conan remotes 不可解析 hdf5/1.13.0，故关闭 HDF5，仅 PDB/内置 netcdf/taurus 驱动）
   - `SILO_BUILD_FOR_BSD_LICENSE=ON`（BSD 变异；HDF5 关闭后 fpzip/hzip/zfp 均不再引入，无 zlib 依赖）
   - `SILO_ENABLE_SHARED=OFF`（静态，规避 `@loader_path` RPATH 问题）
   - `SILO_ENABLE_FORTRAN/PYTHON_MODULE/JSON/BROWSER/SILOCK/SILEX=OFF`
   - `BUILD_TESTING=ON`
2. `cmake.build()`
3. `_run_upstream_tests()`：跑上游 ctest 套件并输出 HMBS 标记（见下）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机编译失败：`Unable to find 'hdf5/1.13.0' in remotes` | 原配方硬依赖 conan 包 `hdf5/1.13.0`，但真机 conancenter/ohpcd 两个 remote 都没有该包；仓库内 hdf5/1.13.0 配方无 conanfile.py（从未真正 publish 为 conan 包） | 关闭 HDF5（`SILO_ENABLE_HDF5=OFF`），改用始终启用的 PDB/内置 netcdf/taurus 驱动（上游官方支持的无 HDF5 配置）。移除 `self.requires("hdf5/1.13.0")`、`_build_folder_for_hdf5()`、HDF5 cache var 注入；`cpp_info.libs=["silo"]`（不再 libsiloh5/hdf5::hdf5） |
| 2 | CMake 不识别 HarmonyOS | CMake 无 HarmonyOS 平台模块，`UNIX` 不置位 | E092：`CMAKE_SYSTEM_NAME=Linux` 别名 |
| 3 | 测试二进制运行时找不到 libsilo | silo 测试用 `CMAKE_BUILD_RPATH "@loader_path/../../lib"`，`@loader_path` 是 macOS 专属，Linux 上不解析 | 静态构建（`SILO_ENABLE_SHARED=OFF`），测试二进制静态链入 libsilo.a，无需运行时 RPATH |
| 4 | 上游测试计数口径 | 纯 CMake/ctest 工程 | `upstream_test_count_method=ctest_entries`；discovered 取 `ctest -N` Total Tests，passed/failed 取 `Testing/Temporary/LastTest.log` 的 `Test Passed.`/`Test Failed.` |
| 5 | test_package 依赖 HDF5 驱动 | 原 test.c 同时在 PDB 与 HDF5 驱动上做写读回；HDF5 关闭后 DB_HDF5 不可用 | test.c 仅保留 PDB 驱动用例；test_package/CMakeLists.txt 移除 `find_package(hdf5)`/`hdf5::hdf5`/`find_library(hdf5)`；marker `discovered:1` |
| 6 | 真机预检失败：`Connection to github.com timed out` | 真机环境 github.com 直连超时（30s ConnectTimeoutError），镜像未启用 | 在 conandata.yml 中改用镜像列表：gh-proxy.com 前置、官方 URL 兜底（与 build_and_test.sh 镜像映射一致，sha256 不变） |
| 7 | 真机编译失败：`Can't untar a tgz containing files in the root with strip_root enabled` | 归档 `Silo-4.12.1.tar.xz` 包含 macOS 资源分支（以 `._` 开头的条目），共 692 个垃圾文件；Conan 的 `get(strip_root=True)` 要求所有文件在单一公共根目录下，遇到多个顶层条目直接报错 | 重写 source() 方法：手动下载归档后，用 Python tarfile 提取时过滤掉所有名称中包含 `._` 前缀的条目（包括 `._Silo-4.12.1/` 根目录及子目录中的资源文件），保留纯净的源码树后移动到 source_folder；删除不再使用的 `get` 导入 |
| 8 | 真机编译失败：`TypeError: download() got an unexpected keyword argument 'checksum'` | `conan.tools.files.download()` 的哈希校验参数名为 `sha256`，不是 `checksum` | 将 `checksum=src_item.get("sha256")` 改为 `sha256=src_item.get("sha256")` |
| 9 | 真机编译失败：`OSError: TarFile is closed` | `with _tf.open(...) as tf:` 上下文管理器在 `getmembers()` 后自动关闭 tarfile，但 `extractall()` 在其外调用，导致操作已关闭的 TarFile | 将 `members` 过滤和 `tf.extractall()` 移入同一个 `with` 块内，确保 tarfile 在 extractall 时仍保持打开状态 |
| 10 | 真机上游测试 57/60 通过，3 个失败：`testdtypes`、`test_mat_compression-basic`、`test_mat_compression-dense`（编译成功，进入 ctest 阶段） | 上游 `tests/CMakeLists.txt` 有三处把依赖已关闭功能的测试注册在 `if()` 守卫之外：①`test_mat_compression-basic/dense` 的可执行文件默认 `driver=DB_HDF5`（源码第 162 行），输出名 `.pdb` 仅文件名、实际仍走 HDF5 驱动，运行时 `DBCreate` 提示需 HDF5 后失败（`unable to open/create file tmc-basic.pdb` / `tmc-dense.pdb`）；而上游自己的 `*-basic-hdf5/*-dense-hdf5/*-gzip-hdf5/*-zfp-hdf5` 同族判例均在 `if(SILO_ENABLE_HDF5 AND HDF5_FOUND)` 内，唯独这两个遗漏（上游疏忽）。②`testdtypes` 是 POSIX shell 脚本，无条件执行 `browser=$(find_file ...); [ $? -eq 0 ] || exit 1`，本配方 `SILO_ENABLE_BROWSER=OFF`（browser 工具未编译），0.22s 即 `exit 1` | 新增源码补丁 `patches/0001-gate-hdf5-browser-dependent-tests.patch`（经 conandata.yml `patches: "4.12.1"` 由 conanfile 的 `apply_conandata_patches` 应用）：把 `test_mat_compression-basic/dense` 移入 `if(SILO_ENABLE_HDF5 AND HDF5_FOUND)`，把 `testdtypes` 整块改为 `if(NOT WIN32 AND SILO_ENABLE_BROWSER)`。与上游其他 `*-hdf5` 用例一致：无 HDF5/无 browser 配置下不注册、不计数，注册集合与上游对该配置的设计一致 |

## 源码修改

- `patches/0001-gate-hdf5-browser-dependent-tests.patch`（经 conandata.yml 由 `apply_conandata_patches` 应用，本仓库变更，非上游代码；`patches_applied` 不再为空）：
  - 把 `test_mat_compression-basic`/`test_mat_compression-dense` 移入 `if(SILO_ENABLE_HDF5 AND HDF5_FOUND)` 守卫（其可执行文件默认 `driver=DB_HDF5`，输出名 `.pdb` 仅文件名，实际走 HDF5 驱动）。
  - 把 `testdtypes` 整块改为 `if(NOT WIN32 AND SILO_ENABLE_BROWSER)` 守卫（shell 脚本无条件要求 silo browser 工具）。
  - 效果：无 HDF5/无 browser 配置下，这三处用例与其他 `*-hdf5` 用例同样不注册、不计数，注册的 ctest 集合（57 个）与上游对该配置的设计一致。

## 依赖版本

- 无外部 conan 依赖（HDF5 关闭；PDB/内置 netcdf/taurus 驱动随 libsilo.a 一起提供）

## 验证结果

（真机 evidence 轮填写）——上游测试以 ctest 套件为准，通过率以真机预检日志里 `HMBS_UPSTREAM_TEST_RESULT` 为准；新增 test_package 以 `HMBS_TEST_PACKAGE_RESULT` 为准。`test_package/MANIFEST.yml` 的 `upstream_test_total` 为 57（对 tests/CMakeLists.txt 逐项分析 + 0001 补丁收纳 3 个依赖已关闭功能的用例），须用真机 `ctest -N` 的 Total Tests 校准。

## 注意事项

- HDF5 关闭后，上游 HDF5_ONLY 用例（compression/grab/largefile/memfile_simple/mk_nasf_h5/partial_io/readstuff/testhdf5/locking）及全部 `*-hdf5` 变体（含 compression-*/multi_test-*/multi_file-*/testdtypes-hdf5/checksums）不注册，不计数、不计缺口（配置层面主动关闭，非静默跳过）。
- 0001 补丁另收纳三个遗漏在 if() 守卫之外的用例：test_mat_compression-basic/dense（默认 driver=DB_HDF5）与 testdtypes（无条件要求 browser 工具）。它们依赖已关闭功能（HDF5/browser），同样不注册、不计数，注册集合与上游对无 HDF5/无 browser 配置的设计一致。
- 若后续真机/ohpcd remote 出现可用的 conan hdf5 包，可重新打开 HDF5 并相应恢复 test_package HDF5 用例。
- 上游 ctest 套件较大，含 DEPENDS/RESOURCE_LOCK/SKIP_RETURN_CODE 机制；`ctest -j1` 串行执行以避免资源锁冲突。
- 测试输出计数只来自 ctest 自身的 LastTest.log 与 `ctest -N`，不做手工推算。

## 补充（2026-09-21）
| 11 | 真机 test_package 失败：`find_package(silo_llnl)` 找不到 silo_llnl config | 包名是 `silo-llnl`（中划线），Conan 2 CMakeDeps 默认按包名生成 `silo-llnl-config.cmake` 与 `silo-llnl::silo-llnl` 目标；而 CMake 标识符不允许中划线，test_package 按惯例用下划线 `find_package(silo_llnl) / silo_llnl::silo_llnl`，名称不匹配 | 在 conanfile.py `package_info()` 中 `self.cpp_info.set_property("cmake_file_name","silo_llnl")` + `set_property("cmake_target_name","silo_llnl::silo_llnl")`，让 CMakeDeps 生成下划线形式的 config 文件与 target，与 test_package/下游消费方对齐 |
| 12 | 真机 test_package CMake 错误：`target_link_libraries` keyword/plain 签名混用 | 上一轮修复后 `silo_llnl::silo_llnl` 目标已正确声明（log: `-- Conan: Target declared 'silo_llnl::silo_llnl'`），但 test_package/CMakeLists.txt 第 8 行用 keyword 签名 `PRIVATE silo_llnl::silo_llnl`，第 18 行 `find_library(SILO_LIB silo)` 命中了安装目录的 libsilo.a，又以 plain 签名 `target_link_libraries(test_silo_llnl ${SILO_LIB})` 追加链接，同一目标混用两种签名触发 CMake 硬错误 | 移除 test_package/CMakeLists.txt 中冗余的 find_library/find_path 回退链接逻辑，仅通过 CMakeDeps 目标 `silo_llnl::silo_llnl` 链接（一个来源，无签名混用） |
