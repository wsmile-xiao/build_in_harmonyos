# deps-report — rocksdb 8.7.3

## 目标库状态
- 软件: rocksdb 8.7.3 (facebook/rocksdb tag v8.7.3)
- 来源: 方式二（依赖库），上游 URL 已提供
- 已在仓库? 否 — `archives/r/rocksdb/` 仅有 6.4.6 / 9.10.0（旧手工适配，无 conan 配方），本任务新增 8.7.3 conan 适配

## 依赖清单表

RocksDB 为 CMake 构建，压缩库可按需启用。R35 铁律：判断 binary 可用性一律 `conan download` 实测（禁用 conan list/search 判存在）。

| 依赖 | 上游要求 | 仓库配方? | cmd-pkgs预编译? | Conan recipe (ohpcd) | 变体 | 结论 |
|------|---------|-----------|----------------|----------------------|------|------|
| zlib | >=1.2 | — | — | ✅ zlib/1.3.1.1 | shared=False | 可用（静态） |
| snappy | >=1.1 | — | — | ✅ snappy/1.2.2 | shared=False | 可用（静态） |
| lz4 | >=1.8 | — | — | ✅ lz4/1.10.0 | shared=False | 可用（静态） |
| bzip2 | >=1.0 | — | — | ✅ bzip2/1.0.8 | shared=False | 可用（静态） |
| zstd | >=1.4 | — | — | ✅ zstd/1.5.6 | **shared=True** | 可用（仅共享）→ 关闭 |
| gflags | >=2.2 | — | — | ✅ gflags/2.2.2 | **shared=True** | 可用（仅共享）→ 关闭 |

> 注：`conan download` 实测均返回对应 binary 的 settings/options，确认 6 个依赖在 ohpcd 均存在。

## 缺口
- **无缺口**：6 个依赖均可用。

## 适配决策说明
- 保留**静态**压缩库 zlib/snappy/lz4/bzip2（WITH_*=ON）。
- 关闭 **zstd / gflags**（ohpcd 仅 shared 变体）。原因：OHOS 容器动态加载器拒绝加载用户可写路径共享库（dlopen Permission denied），若启用则 `librocksdb.so` 需在运行时加载 `libzstd.so.1`，本地 `test_package` 无法运行，无法达到 100% 通过率。关闭后 `librocksdb.so` 仅依赖系统库 `libc++_shared.so`/`libc.so`，本地可完整验证。RocksDB 压缩功能仍由静态的 zlib/snappy/lz4/bz2 提供。
- 上游 `pthread_cond_clockwait` 链接问题未在本容器构建产物 `librocksdb.so` 的 DT_NEEDED 中出现（未列为显式 NEEDED），如需下游链接可参照 6.4.6 使用 `-Wl,--allow-shlib-undefined`。

## 建议顺序
- 全部依赖已就绪，无前置发布需要，直接进入构建（S3）。
