# ChunkIO

chunkio 是 [Fluent Bit](https://fluentbit.io) 使用的 chunk 存储库：它把一段二进制数据
包装成 "chunk"，按流（stream）/块（chunk）的两级结构写入**内存**（memfs 后端）或
**内存映射文件**（fs 后端），并提供 CRC32 校验、内存映射升降级（up/down）、元数据与
统计接口。上游仓库 <https://github.com/fluent/chunkio>，C 语言，CMake 构建，
Apache-2.0 许可。

## 功能概述

- `cio_ctx` 上下文 + `cio_stream` 流 + `cio_chunk` 块的三层 C API
- 两种存储后端：`CIO_STORE_MEM`（纯内存）与 `CIO_STORE_FS`（mmap 文件）
- 可选 CRC32 校验（`CIO_CHECKSUM`）、块内容 up/down、事务（tx begin/commit/rollback）
- 自带 `acutest` 单元测试套件（`tests/`，6 个测试程序 / 24 个注册用例）
- 自带 `cio` 命令行工具源码（本包按 conan-center-index 的做法不构建，产物为纯库）

## OHOS 适配要点

| 问题 | 处置 |
|---|---|
| 上游 0 条 `install()` 规则，装出来是空包 | 补丁 `0001-add-installer.patch`（与 conan-center-index 逐字一致），同时注释掉 `add_subdirectory(tools)` |
| `POSITION_INDEPENDENT_CODE` 被硬写成 ON，`fPIC` 选项失效 | 补丁 `0002-disable-pic.patch`（CCI 逐字一致），PIC 交回 conan `fPIC` / `BUILD_SHARED_LIBS` |
| musl / HarmonyOS 没有 `<fts.h>` | 补丁 `0003-ohos-fts-to-nftw.patch`：`__has_include` 探测，缺失时改用 POSIX `nftw(3)` |
| `fallocate(2)` / `posix_fallocate(3)` 在 HMDFS/tmpfs 上被 EACCES 拒绝（知识条目 **E523** 同族） | 补丁 `0004-ohos-fallocate-ftruncate-fallback.patch`：非 `ENOSPC` 错误降级到 `posix_fallocate`，预分配被拒时最终降级到 `ftruncate(2)` |
| `/tmp` 只读（erofs）导致上游测试建不出上下文 | 补丁 `0005-ohos-tests-tmpdir.patch`：测试临时目录改到构建目录下（**属于对上游测试用例的修改**，PR 正文已申报） |
| CMake 4 移除 `< 3.5` 兼容 | 配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| prescan 报 `mremap` critical | 一手探针实测 `mremap()` 在本设备可用（rc=0），且 fs 测试真实走到 remap 路径全绿 ⇒ 不改源码，已在 `notes.md` 留档 |

## 依赖关系

- 编译依赖：**0**（无 `requirements()`）
- 源码自带子树：`deps/crc32`（编译为 `libcio-crc32.a` 并随包安装）、
  `deps/monkey/include`（`mk_list.h`，`<chunkio/chunkio.h>` 公开包含，必须安装）、
  `tests/lib/acutest`（测试框架，不安装）
- 运行依赖：仅 libc

## 参考资料

- 上游仓库：https://github.com/fluent/chunkio
- 上游 tag：`v1.5.2`（`git ls-remote --tags` 实证存在）
- 源码归档 sha256：`c73e809215454c34a79ed2a7d38abc6058da99dad8564de85e2919100fb987a5`
  （与 conan-center-index `recipes/chunkio/all/conandata.yml` 逐字一致）
- conan-center-index 配方：https://github.com/conan-io/conan-center-index/tree/master/recipes/chunkio
