# minizip-ng 4.2.2 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | minizip-ng（zlib-ng 系现代 zip 操作库） |
| 版本 | 4.2.2（版本跟进件：main 有 4.1.1 历史归档） |
| 状态 | built |
| 构建系统 | cmake（纯 C） |
| 源码 | https://github.com/zlib-ng/minizip-ng/archive/refs/tags/4.2.2.tar.gz |
| sha256 | 71af7b9799856d8b03619df3949e9c1be9703f8de0795af71399ba283cb27aac |

## 版本跟进说明
- main 已有 `archives/m/minizip-ng/4.1.1/`（autotools 时代归档记录，status=built/partial，
  **无 conanfile.py**——非制品仓发布版本）。
- 4.2.2 是上游 tag（2025-02），现代化 cmake 重写 + C API。非重导件：制品仓无 minizip-ng 包。

## 适配要点
1. **纯 C cmake 包**：ohos.toolchain 自发现 + 裸 cmake（同 libzip/1.11.4 范式，ML-0035 绕开）。
2. **依赖接线**：上游 find_package(ZLIB/LibLZMA/OpenSSL/zstd/BZip2)——按 conan 包内
   lib/cmake/<name> 逐个预设 <Name>_DIR（zlib_DIR/OpenSSL_DIR/bzip2_DIR/zstd_DIR），
   配 ohos-find-deps.cmake preload（FIND_ROOT_PATH BOTH）。
3. **功能面**：MZ_ZLIB+BZIP2+ZSTD+OPENSSL=ON（上游默认能力面，让 gtest 全套可跑），
   MZ_LZMA/PPMD=OFF（registry 无 xz_utils/lzma-sdk 包），MZ_ICONV=OFF（musl 无 iconv），
   MZ_LIBBSD=OFF（避免交叉乱猜），MZ_FETCH_LIBS=OFF（CI 离线禁 fetch）。
4. **产物**：lib/libminizip.so + include/mz*.h + mz_compat（unzip.h/zip.h 兼容层）。

## 上游测试
- 上游 gtest 套件（test/*.cc）：**42 用例**（编译展开后实测 42：os/stream/encrypt/compat/
  path/crypt/stream_find 七套件；静态 grep TEST/TEST_F 为 35，参数化用例编译期展开）。
- CI 离线不可跑（gtest 需 FetchContent）；**本地已真实执行**：registry gtest/1.17.0 构建，
  从源码根目录起跑（数据文件 CWD 依赖），`[ PASSED ] 42 tests.`（0 FAILED，exit 0）。
- 上游测试代码未修改。

## 依赖
- zlib/1.3.1.1、openssl/3.5.6.1.2、bzip2/1.0.8.2、zstd/1.5.7（全部已发布制品仓 ✅）
