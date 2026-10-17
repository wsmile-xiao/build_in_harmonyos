# onak

`onak` 是一个 OpenPGP 兼容的密钥服务器，核心库 `libonak` + 可插拔的密钥数据库
后端（`keydb/`）。本适配构建并安装 `onak` 及配套工具、CGI 与后端共享库。

## 适配要点

- **构建**：CMake，`DBTYPE=dynamic`（构建全部后端 `libkeydb_*.so` 供运行时 dlopen），关闭 keyd（无 systemd）。
- **依赖**：`nettle` + `hogweed` + `gmp`（Conan）。上游用 `pkg_check_modules`，本配方改为 CMakeDeps 的 imported targets。BDB/HKP(libcurl)/PostgreSQL 后端在 OHOS 上不可用，已关闭。
- **补丁（5 个）**：
  1. lld 不支持 `libonak.ld` 的 `INSERT AFTER .text`，删除之（符号已由 `-Wl,-export-dynamic` 导出）；
  2. `CMakeLists.txt` 用 imported targets 取代 pkg-config；并显式设置 `have_nettle_get_secp_*r1`（本工具链 `try_compile` 不可靠）；
  3. `keydb/CMakeLists.txt` 去掉 libcurl/libpq 探测；
  4. `onak.c` 的 `strtouq`（bionic 无）改为 `strtoull`；
  5. `keydb/keydb_fs.c` 的硬链接（**HMDFS 不支持，`link()` 返回 EPERM**）回退为 symlink。

## 上游测试

`runtests`（CMake 里注册为 ctest `sanitytests`）遍历已构建的后端 `libkeydb_*.so`，对每个后端运行对应 `t/<backend>-*.t` 与全部 `t/all-*.t`。构建时实跑 `sh runtests` → `** all tests succeeded (47)`。

## 消费者测试

`test_package/test_onak.sh`：用安装后的 `onak` + 打包的 `file` 后端做 add → get（长/短 keyid）→ delete 往返，6 项断言。

## 产物

| 路径 | 说明 |
|---|---|
| `bin/onak`、`bin/splitkeys`、`bin/stripkey`、`bin/maxpath`、`bin/sixdegrees`、`bin/wotsap` | 命令行工具 |
| `lib/libonak.a` | 核心静态库 |
| `lib/onak/backends/libkeydb_*.so` | dummy/file/fs/keyring/stacked 后端 |
| `share/man/man1/*.1` | man 手册 |

## 参考

- 上游：<https://www.earth.li/projectpurple/progs/onak.html>
