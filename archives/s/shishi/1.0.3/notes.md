# shishi 1.0.3 适配笔记

## 编译环境
- 构建系统: autotools（官方 release tarball 自带 configure / Makefile.in / gengetopt 生成物）
- 编译日期: 2026-09-23
- 编译器: clang/clang++
- 状态: built

## 编译步骤

源必须用官方 release tarball（`https://ftp.gnu.org/gnu/shishi/shishi-1.0.3.tar.gz`，sha256 `95798ffd12dd01a4f88e0311ee03ca4a26e5cb4e5e9059a40e4fc4d9f2917e92`，上游 tag `v1.0.3` 实核）。
配方 `generate()` 注入 configure 参数后按 autotools 标准链执行：

```
./configure --prefix=<prefix> \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  --with-libgcrypt-prefix=<libgcrypt conan 包前缀> \
  --disable-gtk-doc --disable-nls --without-stringprep --disable-starttls --disable-pam
make -j2
make check          # tests/ 的 16 个 automake TESTS 用例，纳入构建契约
make install        # install-data-hook 会在 DESTDIR 下初始化 Shisa DB + 生成 host key
```

依赖 include/lib 路径由 conan `AutotoolsToolchain.extra_cflags/extra_ldflags` 按 `cpp_info` 显式注入（conan 2.29 的 AutotoolsToolchain 不自动注入依赖路径）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type`，`config.guess: can't create .../cgXXXXXX/dummy.c: Permission denied` | ① 设备 `uname -s` 返回 `HarmonyOS`，上游 2022-05-25 的 config.guess 不识别（E007 现场）；② config.guess 的 `set_cc_for_build` 用 `mktemp -d` 建临时目录，HMDFS 上落盘为 `drwx--S---`(2700) 不可写（设备事实 §一.10：本机实测普通 `mkdir` 可写、`mktemp -d` 不可写） | 配方在 OHOS 下显式传**等值** `--build/--host=aarch64-unknown-linux-gnu`，configure 不再调用 config.guess；设备实测 `checking whether we are cross compiling... no`，gnulib 运行期检查（working mktime 等）照常执行，非交叉编译 |
| 2 | configure 后段 `config.status` 创建 `./confXXXXXX` 同样走 `mktemp -d` → `could not setup config files machinery` | 同上 HMDFS mktemp 语义 | `patches/0001-configure.patch`：mktemp 分支改普通 `mkdir`（abnfgen/E011/E114 先例） |
| 3 | `configure: error: libgcrypt is too old`（`checking for LIBGCRYPT - version >= 1.4.4... no`） | 上游这段探测只认 `libgcrypt-config`，没有 pkg-config 回退；系统与默认 PATH 中没有它 | `--with-libgcrypt-prefix=<conan libgcrypt 包前缀>`（包内 `bin/libgcrypt-config` 实测报 1.12.2）；其输出的 `-I//include`/`-L//lib` 为构建期陈旧前缀，靠 extra_cflags/extra_ldflags 兜底 |
| 4 | `make check`/`make install` 在 `doc/` 报 `makeinfo: inaccessible or not found ... Error 127` | 上游 doc/Makefile 时间戳链 `stamp-vti: shishi.texi configure → version.texi → shishi.info`；我们的 configure 补丁使 configure 变新 → 链条重算 → 要求 makeinfo 重建 info 手册；设备/CI 均无 makeinfo，ohpcd 也未发布 texinfo | 配方 `build()` 中对 `doc/{stamp-vti,version.texi,shishi.info*}` 仅对齐 mtime（内容零改动）标记随包发布的生成物为最新。**不要**改用 `MAKEINFO=true`：该规则先把已发布 `shishi.info*` 挪进临时目录，`true` 不会生成新文件，退出码仍 0，文档会被直接删掉 |
| 5 | `doc/stamp-vti`/`doc/version.texi` 内容一度被**整个环境变量导出**覆盖（含凭证），差点被 refresh-patch 打成补丁入库 | 上游 `build-aux/mdate-sh` 解析 toybox `ls -L -l -d -n /` 输出失败（`failed parsing ... output`）→ 返回空 → 规则里 `set \`\``（零参数）在 mksh 系 shell 下打印全部 shell 变量，重定向进了 `vti.tmp` | 已还原为基线内容并删除误生成补丁；问题 #4 的时间戳对齐使该规则不再触发。已记 `feedback/pending/`（高收益：凭证入补丁近失事件） |
| 6 | 无 `gengetopt`（设备与 CI 均无，ohpcd 也未发布） | `src/*_cmd.c`/`*_cmd.h` 命令行解析器是 gengetopt 从 `*.ggo` 生成的（`BUILT_SOURCES` 显式规则）；git 树只有 `.ggo` | 源锚定官方 release tarball（自带生成物且 mtime 新于 `.ggo`，make 不会重生成）；**不使用 git 快照/归档**。路径 B 草稿 E670 |
| 7 | 采信轮首轮 G2：16 个上游测试全 FAIL（exit 127，`Error loading shared library libgcrypt.so.20`） | conan create 的 build() 进程没有 conanrun 环境；libtool 只对带 `.la` 的依赖记 rpath（libtasn1/libgpg-error 有、libgcrypt 只有 `.so`），运行期 loader 找不到 libgcrypt（探索轮通过是因手工导出了 LD_LIBRARY_PATH，属环境差异而非配方差异） | 配方 `build()`/`package()` 起手调 `_ensure_run_libs()`：把全部依赖 libdir 前置注入本进程 `LD_LIBRARY_PATH`（先例 srecord/1.65.0 `_ensure_run_libs`，知识 E019）；test_package `test()` 同法防御（OHOS conanrun 可能省略 LD_LIBRARY_PATH）。产物不嵌机器私有 rpath（规避 E537 的可搬运性问题）。修复后 G2 干净轮 **TOTAL 16 / PASS 16 / FAIL 0** |
| 8 | 采信轮第二轮走到 test_package 后断言 4（`shisa_init` 默认初始化）FAIL（`//etc/shishi/shisa.conf` 缺失 + `Cannot initialize file database backend. Location //var/shishi`）；同根因令上游 install-data-hook 的 `shisa -a` 失败留下 0 字节 `shishi.keys`；另包内无 `sbin/` | ① conan 以 `--prefix=/ + DESTDIR=<包目录>` 布局安装（文件借 DESTDIR 落进包内），而 shishi 把系统配置/数据库路径编译成**宿主绝对**位置，运行期读宿主 `/etc`、`/var` 而非包内目录 ⇒ 消费者默认初始化与打包期建库都必然失败；② hook 里的 `shisa -a` 还叠加了构建进程无 `LD_LIBRARY_PATH` 的 exit 127（hook 吞掉返回码只打印 "Unable"）；③ conan `AutotoolsToolchain` 把 `--sbindir` 映射到 `bindirs[0]`，`shishid`/`keytab2shishi` 因此装进 `bin/`（包内实核 5 工具全在 `bin/`，`sbin/` 在包内不存在属映射结果、非丢失） | 断言 4 改为**探针实测 rc=0** 的确定性行为：运行时自写 cfg（`db file tshisa-db`）+ 可写目录后 `shisa_init_with_paths`（`cwd` 指到 gitignore 的 `test_package/build/`，零提交面污染）；`package()` 清理 0 字节 `shishi.keys` 并在 notes/PR 已知限制登记「建库属部署动作」；工具冒烟与 `cpp_info.bindirs=["bin"]` 对齐 sbin→bin 折叠，5 工具逐个 `--version` 实跑 |

## 源码修改

- `patches/0001-configure.patch` — config.status 临时目录创建：mktemp 分支改为 `tmp=./conf$$-$RANDOM && mkdir "$tmp"`。
- 时间戳对齐（非补丁、零 diff）：`build()` 里对 `doc/stamp-vti`、`doc/version.texi`、`doc/shishi.info*` 调 `os.utime`，只改 mtime 不改内容。路径 B 草稿 E676。

## 依赖版本

- 硬依赖（configure.ac `AC_MSG_ERROR` 两处）：`libgcrypt/1.12.2`、`libtasn1/4.21.0` —— 均 `conan list -r=ohpcd` 实查已发布，且 `conan install --build=never` 实测拉到二进制（连带 `libgpg-error/1.55`）。
- 可选依赖按缺省禁用：libidn（ohpcd 无发布，`--without-stringprep`）、gnutls STARTTLS（`--disable-starttls`）、PAM（`--disable-pam`，设备无 pam 头）。
- NLS（`--disable-nls`）：设备只有 harmonybrew 有 msgfmt，CI worker PATH 无 harmonybrew（设备事实 §一.4），故关闭。

## 验证结果

```bash
# 探索轮（树外构建，2026-09-23，日志 $TASK_DIR/explore.log）
./configure ...        # rc=0
make -j4               # rc=0
make check             # rc=0 → tests/: TOTAL 16 / PASS 16 / FAIL 0（automake 测试摘要原文）
make install DESTDIR=… # rc=0（install-data-hook 在 DESTDIR 下建库+host key）
# 安装树 5 个工具 --version 全部 rc=0 并自报 1.0.3
# 采信轮（conan create，同一 SHA）结果见 reports/conan-create.log 与 reports/test-report.md
```

## 注意事项

- 上游 `make check` 只注册 `tests/` 的 16 个 C 用例；`tests/shisa.sh`、`tests/check_docbook.sh` 仅在 `EXTRA_DIST`，上游 `make check` 不运行（差额归因见 PR 正文）。
- 测试 fork 本地 KDC 走 127.0.0.1：回环属本地行为；16 个用例实测全部通过，未牵出真实外网 DNS/时间同步（任务卡风险 1 已核）。
- **宿主绝对路径边界**：conan 以 `--prefix=/ + DESTDIR` 布局打包，而 shishi 把系统配置/数据库路径在编译期写成宿主绝对位置——包内 `etc/shishi/*.conf`、`var/shishi` 只是模板与目录占位，消费者运行期须显式指定（`--system-configuration-file`、`--ticket-file` 等）。上游 `install-data-hook` 想在打包期建库+host key 因此必然失败（`shisa -a` 读宿主 `/etc`、`/var`），其留下的 0 字节 `shishi.keys` 已由 `package()` 清理，**建库属部署动作**（PR 已知限制同步登记）。
- 5 个命令行工具全部位于 `bin/`（conan `AutotoolsToolchain` 把 `--sbindir` 折入 `bindirs[0]`），包内不存在 `sbin/` 属映射结果、非丢失；`cpp_info.bindirs=["bin"]` 与实物对齐。
