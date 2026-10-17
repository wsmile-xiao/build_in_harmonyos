# onak 0.6.5 OHOS 适配记录

平台任务 `contrib-9161`，`onak 0.6.5`，`taskBranch=feat/onak-0.6.5`，路径 A。

## 源码

- Debian orig：`https://deb.debian.org/debian/pool/main/o/onak/onak_0.6.5.orig.tar.xz`
- `sha256 = 84bfe7fd0fa410e87dd06505d408948c8a2098f5bd00648b9dee37af7167ef39`

## 依赖与配置

- `nettle/3.9.1` + `hogweed/3.9.1`（+ 传递 `gmp`）。nettle 与 hogweed 对 gmp 的 pin 不同（6.3.0 vs 6.3.0.1），用 `gmp/6.3.0` override。
- CMake：`DBTYPE=dynamic`、`KEYD=OFF`、`CMAKE_DISABLE_FIND_PACKAGE_BDB=TRUE`。
- 每个库都需 `CMakeDeps`（否则 `find_package` 找不到）。

## 补丁（5 个）

| # | 文件 | 原因 |
|---|---|---|
| 0001 | `libonak.ld` | lld 不支持 `INSERT AFTER .text;`；`EXTERN` 符号已由 `-Wl,-export-dynamic` 导出，删除该行 |
| 0002 | `CMakeLists.txt` | 用 `find_package(nettle/hogweed/gmp CONFIG)` + imported targets 取代 `pkg_check_modules`；`try_compile` 在本工具链不可靠，直接 `set(HAVE_NETTLE_GET_SECP_*R1 true)`；并显式 `target_include_directories(... ${GMP_INCLUDE_DIR})`（Conan gmp 包未导出 includedirs） |
| 0003 | `keydb/CMakeLists.txt` | 移除 libcurl/libpq 后端探测（OHOS 无） |
| 0004 | `onak.c` | `strtouq` 在 bionic 不存在 → `strtoull` |
| 0005 | `keydb/keydb_fs.c` | **HMDFS 不支持硬链接**（`link()` 返回 EPERM），词/子钥/skshash 索引条目回退为 symlink |

## 关键实测：HMDFS 无硬链接

真机上：`echo hi > a; ln a b` → `ln: cannot create hard link from 'a' to 'b': Operation not permitted`；`ln -s` 正常。

onak 的 `fs` 后端用 `link()` 为每个「词/子钥/skshash」索引建硬链接到密钥文件。硬链接失败 → 7 个 `all-*.t`（按文本/哈希/子钥检索）在 `fs` 后端下报 `Key not found`。补丁 0005 改成 `link()` 失败时用 `symlink()`，47/47 全过。

> 若日后要申报路径 B：这是「HMDFS 读写语义」的一个具体实例（硬链接不可用）；但需先按 `tools/kb-check.mjs` 对 `hard link`/`link()`/`fs` 族查重，且要证明是可修 + 可复用的一类机制。本轮按路径 A 提交。

## 上游测试

- `runtests`（即 ctest `sanitytests`），构建时实跑：`** all tests succeeded (47)`。
- 计数：已构建后端 dummy/file/fs/keyring/stacked；`dummy` 跑 `t/dummy-*.t`，其余跑 `<backend>-*.t` + 全部 `t/all-*.t`，共 47 次脚本调用。

## 消费者测试

`test_package/test_onak.sh`：使用安装后的 `onak` 与打包的 `file` 后端，add → get（长/短 keyid，含 uid）→ delete → 再 get 报 `Key not found`，6 项断言。

## 结果

- 真机 `conan create` 退出码 0；上游 47/47、消费者 6/6。
