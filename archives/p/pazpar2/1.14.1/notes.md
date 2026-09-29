# pazpar2 1.14.1 适配笔记

## 编译环境
- 构建系统: autotools（上游 `make dist` 发行包，自带 configure/Makefile.in）
- 编译日期: 2026-09-28
- 编译器: clang 15 / clang++（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

上游发行包已含生成的 `configure`，无需 autoreconf（本机也只有 autoconf 2.72，缺 automake/libtool）。

```bash
conan create archives/p/pazpar2/1.14.1 --build=missing     # exit 0
```

配方内实际执行：

1. `source()`：`get()` 拉官方 tar.gz（ftp.indexdata.com，与 yaz 同源）→ 应用 3 个 patch → 把 vendored `configure`/`aclocal.m4`/`*.in` 重新 utime 到最新（掐断 make 的 aclocal/automake 重生成）。
2. `generate()`：`AutotoolsDeps` + `AutotoolsToolchain`；追加 `--disable-dependency-tracking`、`--with-yaz=<yaz>/bin`，并用 `extra_ldflags` 注入各依赖 lib 目录的 `-Wl,-rpath`。
3. `build()`：`configure` → `make -j1`（HMDFS 下 GNU make jobserver 的 FIFO 不可用，保持串行）。
4. `package()`：`make install`（Autotools 自动带 `DESTDIR=<package_folder>`，`--prefix=/`）→ 拷贝 LICENSE。

产物：`bin/pazpar2`（上游 sbin）、`bin/pazpar2_play`、`share/man/man{1,5,7,8}/*`、`share/doc/pazpar2/*.html`、`share/pazpar2/js/pz2.js`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure`：`unable to guess build type` / `system 'ohos' not recognized` | 自带 config.guess(2018)/config.sub 不识别 HarmonyOS | patch 0001：config.guess 加 `*:HarmonyOS:*` 分支输出 `${MACHINE}-unknown-linux-ohos`；config.sub 加 `linux-ohos*` 两处。零 `--build/--host` 参数 |
| 2 | `configure`：`cannot run C compiled programs`（`Error loading shared library libxml2.so.16`） | 制品仓 libxml2/2.15.3 是共享库；autotools conftest 要被执行，构建期无 LD_LIBRARY_PATH | `AutotoolsToolchain.extra_ldflags` 注入 `-Wl,-rpath,<dep>/lib`（同时使最终二进制可加载 libxml2） |
| 3 | `configure`：`YAZ development libraries missing` | pazpar2 通过 `yaz-config` 定位 YAZ；yaz 包未把 bin/ 放进 buildenv PATH | `--with-yaz=<yaz package_folder>/bin` |
| 4 | `configure`：`YAZ not compiled with Libxslt support` | 制品仓 yaz/5.37.3 构建时 `--with-xslt=no` | patch 0003：该检查降级为警告（pazpar2 自身直连 libxslt/libxml2，所用 yaz API 全部由 libyaz.a 无条件导出），并在配方显式 `requires("libxslt/1.1.45.2")`（libxml2 显式声明以直接使用其头文件） |
| 5 | `make`：`aclocal-1.16: command not found` → Error 127 | patch 过 configure.ac 后它比 vendored aclocal.m4/Makefile.in 新，make 触发 automake 重生成 | `source()` 中把 `configure`/`aclocal.m4`/`config.h.in`/`Makefile.in` 统一 utime 到最新 |
| 6 | `config.status`：confXXXX 目录权限/`mktemp` 问题（HMDFS） | configure 用 `umask 077` 建临时目录，HMDFS 忽略 owner-only 模式 | patch 0002：2 处 `umask 077` → `022` |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-config-guess-sub-ohos.patch | `config/config.guess`、`config/config.sub` | HarmonyOS/ohos 平台识别（1 + 2 处） |
| 0002-configure-hmdfs-umask.patch | `configure` | `umask 077` → `022`（2 处） |
| 0003-configure-yaz-xslt-optional.patch | `configure.ac`、`configure` | YAZ 的 XSLT 硬检查 → 警告（源码层 + 生成脚本对应位置同步） |

补丁由 `.orig`（tar 解压基准树）/`.work`（工作树）逐文件 `diff -u` 生成，分 3 个阶段（S1 平台识别 / S2 umask / S3 XSLT），`git apply --check` 全过且应用后与 `.work` 树 `diff` 为空。补丁内无 `__OHOS__` 等平台宏。

## 依赖版本

- yaz/5.37.3（Z39.50/SRU 工具包，ohpcd 已发布；`--with-xslt=no` 构建）
- libxslt/1.1.45.2（pazpar2 直接 include `<libxslt/*.h>`）
- libxml2/2.15.3（yaz/libxslt 共用，共享库 `libxml2.so.16`）

依赖发布状态用 `conan download <ref> -r=ohpcd --only-recipe` 逐个实证（R35/R36）。

## 验证结果

```bash
# 1) 干净构建 + 消费者测试
conan create archives/p/pazpar2/1.14.1 --build=missing
#   → exit 0；test_package 11/11 断言通过

# 2) 上游测试（本机 OHOS PC 实测，yaz bin 加入 PATH 以启用 yaz-ztest 目标）
cd <build_folder> && . build-release/conan/conanbuild.sh && PATH=<yaz>/bin:$PATH make check -j1
#   src/      : TOTAL 2  PASS 2
#   etc/xsl/  : TOTAL 1  PASS 1
#   test/     : 14 个 TESTS，12 PASS / 2 FAIL（test_http.sh、test_post.sh）
#              其中 test_icu/test_perf/test_solr/test_termlist_block/
#              test_limit_limitmap/test_sort 6 个因 yaz 无 ICU 自动 skip
#              （harness 记 PASS 并打印 "Skipping ...: ICU support unavailable"）
```

失败 2 项归因：`test_http.sh` / `test_post.sh` 是唯一对比**外部** Z39.50 服务器 `z3950.indexdata.com` 现网数据的用例，上游 2021 年的 `.res` 基线已与现网数据集不符（多出记录 "Internet: mailing lists"，`<merged>/<total>` 由 10 变 11、部分 checksum 变化）；其余同结构、用本地 `yaz-ztest` 目标的用例（test_sru/test_facets/test_filter/test_url/test_turbomarcxml/test_settings 等）全部通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/pazpar2` | 元搜索聚合守护进程（HTTP `/search.pz2`，聚合 Z39.50/SRU/Solr 目标） |
| `bin/pazpar2_play` | 上游附带的命令行播放/调试工具 |
| `share/man/man{1,5,7,8}/*` | pazpar2 / pazpar2_play / pazpar2_conf / pazpar2_protocol 手册 |

## 注意事项

1. 上游 `make install` **不安装** `etc/`（无 Makefile.am，仅进 dist 包）与 `etc/xsl/*.xsl`。部署时需自备 pazpar2 配置（`<server><listen/><service>…`）、service/settings 定义与归一化 XSLT。这也是上游 Debian 包拆成 `pazpar2-xsl` 等子包的原因。
2. ICU 功能不可用：制品仓 yaz 为 `--with-icu=no`，`pazpar2 -V` 显示 `icu:disabled`，6 个 `--icu` 上游用例自动跳过。pazpar2 核心（会话、聚合、XSLT 归一化、HTTP 协议）不依赖 ICU。
3. 依赖 `libxml2.so.16` 为共享库，二进制通过 `-Wl,-rpath` 指向 conan 依赖目录；用 `conanrun` 环境运行同样可用。
4. 交叉编译产物为 OHOS aarch64 ELF，仅能在 OpenHarmony/HarmonyOS PC 环境运行（本机即目标平台）。
