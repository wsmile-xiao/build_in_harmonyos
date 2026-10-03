# merecat 2.31-git20260330 适配笔记

## 编译环境
- 构建系统: autotools（git 快照，不含 configure）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4，target aarch64-unknown-linux-ohos
- 状态: published

## 版本说明
- 采用上游 `2.31-git20260330`，对应 Debian `2.31+git20260330+ds-1`（2026-03-30 打包）。
- 源码取 GitHub 快照 commit `57a2ce7c0cca`（2026-03-15），与 Debian 打包时的 HEAD 一致；
  与 Debian orig tarball 逐文件比对，130 个文件 SHA256 全部一致。
- 上游 `configure.ac` 在 2026-03 已升到 3.00-rc1，因此 `merecat -V` 输出 `3.00-rc1`。

## 编译步骤
```bash
sh ./autogen.sh                     # 生成 automake/autoconf 产物，需要 automake
sh ./configure --prefix=<pkg> \
    --enable-builtin-icons --enable-htaccess --enable-htpasswd --without-symlinks
make -j1
make install
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 报 `unable to guess system type` | 未识别 HarmonyOS（E007） | 扩展 aux/config.guess 增加 `*:HarmonyOS:*:*)` 分支返回 aarch64-unknown-linux-ohos；config.sub 接受 ohos-linux 等写法 |
| 2 | `configure` 报工作目录无法确定（E114） | HMDFS 下 `mktemp -d` 产物为 2700+setgid，写入被拒 | 给 configure 指定预先创建的可写目录 `ac_tmp=$tmp`，不再依赖临时目录 |
| 3 | 静态文件访问 403 `non world-readable file` | HMDFS 无 POSIX other 位，目录恒为 750，`S_IROTH/S_IXOTH` 判定失效 | patches/0002 新增 `httpd_other_bits_hidden()`，按 `st_dev` 缓存一次文件系统能力探测，仅在 other 位确实不可用时回退 `access(2)`（POSIX 兼容，R8） |
| 4 | 目录列表 500 `tmpfile: Read-only file system` | `tempfile()` 固定用 `/tmp`，而鸿蒙 PC 的 `/tmp` 只读 | patches/0001 让 `tempfile()` 优先用 `$TMPDIR`，O_TMPFILE 不可用时回退 mkstemp |
| 5 | CGI 返回 403 `is a CGI but not executable` | CGI 可执行判定依赖 `S_IXOTH` | 同上：`S_IXOTH` 不可用时该判定回退 `access(X_OK)`，可用时保持上游语义 |
| 6 | `make check` 依赖 curl/gzip/python3 | 测试套件需要这些工具与 HTTP 客户端 | 由构建环境提供依赖，并在 build() 内执行测试 |

## 源码修改
- `patches/0001-lib-tempfile.c.patch`：`tempfile()` 改用 `$TMPDIR`，O_TMPFILE 不可用时回退 mkstemp。
- `patches/0002-src-libhttpd.c.patch`：新增 `httpd_other_bits_hidden()`，把 `httpd_accessible()`/
  `httpd_executable()` 的 6 处 `S_IROTH/S_IXOTH` 判定改为「文件系统能表达 other 位就保留上游判定，
  否则回退 `access(2)`」。能力探测在 `$TMPDIR` 建一个 0777 文件读回 other 位，按 `st_dev` 缓存，
  且只在临时目录与目标文件同设备时采信；因此普通 Linux（other 位可用）行为与上游逐字一致，
  只有 HMDFS 这类隐藏 other 位的文件系统才走回退。

## 复查修复记录（2026-10-01）

- 依据 PR #13785 的 code review 复核意见修正 `patches/0002`（P1/P2）：原实现**无条件**回退
  `access(2)`，在能表达 other 位的文件系统（普通 Linux）上把「服务器进程可读」当成
  「world-readable / world-executable」，会让 `0600` 静态文件被 200 返回、`0700` CGI 可被远程
  执行。现在只有文件系统确实隐藏 other 位时才回退，能力探测结果按设备缓存，目录列表不会再逐项
  探测（P3-1）。
- `conanfile.py` 的 `_pin_configure_tmpdir()` 用 `shlex.quote()` 包裹写进 `configure` 的
  `$TMPDIR` 值，避免路径含空格或 shell 元字符时脚本语法错误（P3-2）。
- `test_package/test.sh` 增加 world-readable 回归用例：`0600` 文件在能表达 other 位的文件系统上
  必须仍返回 403，在隐藏 other 位的文件系统上按回退返回 200。

## 复查修复记录（2026-10-03）

- `test_package/test.sh` 的 other 位探针（review 192443231，P2）：原来的
  `ls -l "$probe" | sed 's/.* \(...\)$/\1/'` 贪婪匹配到行尾文件名，非 mode 位，导致探针恒判
  `hidden`——`visible` 分支（`0600` → 403 回归断言）成为死代码，且在如实上报 other 位的文件系统
  （普通 Linux、CI）上会把返回 403 的正确行为误判为 FAIL。现在直接对 `ls -l` 行首 mode 字段做
  shell 模式匹配（`case ... in ???????rwx*)`），第 8-10 个字符即 others 的 `rwx`；只用内建语法，
  不引入 `sed`/`cut`/`awk` 依赖，避免受限 PATH（E386 环境）下探针不可用。
- `test_package/test.sh` 的递归删除（review 192438012，P3）：新增 `safe_rm_rf()`，拒绝空值、`/`、
  `.`、`..`、以 `/.` 或 `/..` 结尾、以及不在根目录之下的相对路径，`rm -rf` 只在通过校验后执行；
  退出 trap 同样走该函数。
- `patches/0002` 的 `access(2)` 回退（review 192438012，P2，可选加固）：保留现实现并在此说明边界。
  HMDFS 会把 other 位掩掉（目录恒为 `750`、文件读回恒为 `0600`），此时 POSIX 语义下没有任何可用于
  判定「world-readable」的证据，`access(2)` 是当前平台可得的最接近等价物；若改为在这些文件系统上
  一律拒绝，打包后的服务器在鸿蒙 PC 上会把全部静态内容返回 403，等于库不可用。回退被严格限定：
  仅当能力探测（同设备 `$TMPDIR` 建 0777 文件读回）证明该文件系统隐藏 other 位时才生效，普通
  Linux 上的判定与上游逐字一致。

## 依赖版本
- libconfuse/3.3（配置文件解析）；openssl/3.5.6.1（HTTPS）；zlib/1.3.1（gzip deflate）
- automake/1.18（构建期引导，tool_requires）

## 验证结果
```bash
make check
# TOTAL: 14  PASS: 13  FAIL: 0  SKIP: 1 (php-cgi 未安装，脚本 exit 77)
```
消费者用例 `test_package/test.sh` 已启动打包后的 merecat，通过 HTTP GET 取回内容，并回归验证
world-readable 契约（`0600` 文件：能表达 other 位返回 403，隐藏 other 位走 `access(2)` 回退返回 200）。

## 注意事项
- 不加 `--without-symlinks` 时会创建 `httpd`/`in.httpd` 符号链接，HMDFS 下 `ln -sf` 可能失败，因此保留该选项。
- `merecat -V` 的版本号来自 `configure.ac`（3.00-rc1），与快照日期版本不同，属上游现状。
---

**编译结束**: 2026-09-29 14:27
**最终状态**: published
