# libzippp 7.1-1.10.1 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libzippp（libzip 的 C++ 封装） |
| 版本 | 7.1-1.10.1（上游 tag libzippp-v7.1-1.10.1） |
| 状态 | built |
| 构建系统 | cmake |
| 源码 | https://github.com/ctabin/libzippp/archive/refs/tags/libzippp-v7.1-1.10.1.tar.gz |
| sha256 | 9ded3c4b5641e65d2b3a3dd0cbc4106209ee17c17df70e5187e7171420752546 |

## 上游版本选择说明
- 派工指定 `v6.2-1.x`，但上游仓库已从 **ctasada/libzippp 迁移到 ctabin/libzippp**（旧地址 404）。
- 现上游 tag 序列：v6.0-1.9.2 → v6.1-1.9.2 → v7.0-1.10.1 → v7.1-1.10.1（**无 v6.2**）。
- W0 核验：制品仓 libzip=1.11.4（W0 核版本）；上游 master（2025-06-02 起）已跟进 libzip 1.11.4。
- 按派工口径"tag v6.2-1.x 或 W0 核精确 tag"——选 **v7.1-1.10.1**（最新 release，兼容 libzip 1.11.4）。

## 适配要点
1. **纯 CMake 包**：单源文件 src/libzippp.cpp + 头 src/libzippp.h，C++11。
2. **依赖接线（关键坑）**：上游 MODULE 模式 `find_package(LIBZIP)` 用自带 `cmake/FindLIBZIP.cmake`：
   - `find_path(LIBZIP_INCLUDE_DIR zip.h)` → 预设 `-DLIBZIP_INCLUDE_DIR=<libzip包>/include`
   - `find_library(LIBZIP_LIBRARY zip)` → 预设 `-DLIBZIP_LIBRARY=<libzip包>/lib/libzip.so`
   - `find_file(_libzip_pkgcfg libzip.pc)` → 预设 `-D_libzip_pkgcfg=<libzip包>/lib/pkgconfig/libzip.pc`
   - FindLIBZIP.cmake 内部还有 `find_package(ZLIB REQUIRED)` → 预设 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY
   - 交叉链 FIND_ROOT_PATH=ONLY 会阻断 sysroot 外搜索，不预设会 find 不到（libzip/1.11.4 同款经验）。
3. **选项**：`LIBZIPPP_BUILD_TESTS=OFF`（上游测试需在本机跑，CI 离线不跑）、`LIBZIPPP_ENABLE_ENCRYPTION=OFF`（避免引 openssl 链）、`LIBZIPPP_GNUINSTALLDIRS=ON`（装 lib/ 而非根目录散装）。
4. **产物**：lib/libzippp.so（动态，PREFIX="" 去重前缀）+ include/libzippp/libzippp.h + share/libzippp/ cmake config（find_package(libzippp CONFIG) 可用）。
5. 签名：package 后对 lib/*.so 走 binary-sign-tool 自签（XPM 要求）。

## 上游测试
- 上游 tests/tests.cpp 含 25 个测试函数（test1~test24 + test23_2），make test 形态（add_test 单可执行）。
- CI 离线跑不了上游测试套件（需真实文件系统交互）——本地 conan create 时 test_package 以真实
  建包/读回往返（addData→close→getEntry→readAsText）覆盖核心链路（8 断言）。
- 上游测试代码未修改（LIBZIPPP_BUILD_TESTS=OFF 只是构建开关，不改源）。

## 依赖
- libzip/1.11.4（已发布制品仓 ✅）→ 传递 zlib/1.3.1.1
