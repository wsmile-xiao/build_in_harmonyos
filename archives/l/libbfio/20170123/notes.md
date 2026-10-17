# libbfio 20170123 适配笔记

## 编译环境

- 构建系统: autotools（上游自带生成的 configure，无需自举）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标: OpenHarmony PC aarch64（conan profile `ohos-aarch64`，os=OHOS / arch=armv8）
- 状态: built

## 软件与版本溯源

libbfio 是 libyal 取证家族的基础 I/O 抽象库（文件/内存/文件池/范围 IO），
纯 C，全部内部依赖（libcerror/libcthreads/libcdata/libcfile/libcpath/
libcsplit/libclocale/libcnotify/libuna）以 standalone 形式内嵌在源码树内，
configure 无任何 PKG_CHECK_MODULES/AC_CHECK_LIB 外部探测 → 无 Conan 依赖
（W0 结论：`--deps ""`，配方缺失于制品仓属净新适配，版本未被占用）。

上游 GitHub 仓库（libyal/libbfio）在 2023 年前后重置，2026-06 之前的历史
tag/release 全部不存在（GitHub API 实测仅剩 20260612/20260623 两个 release），
20170123 的官方资产 `libbfio-experimental-20170123.tar.gz` 已无法获取。
本包改用 Debian 的 pristine orig tarball，并以其 PGP 签名的 .dsc 锚定内容：

```bash
$ curl -sS https://deb.debian.org/debian/pool/main/libb/libbfio/libbfio_20170123-6.dsc
# Checksums-Sha256:
#  d45eaa2c7bc5d75905bbd1d04f9730e17bb4b638417343db1af410f3b17a15dd 1948359 libbfio_20170123.orig.tar.gz
# 源版本 20170123-6：无 +dfsg、无 debian/patches 注入 orig 的重打包标记，
# tarball 顶层目录即 libbfio-20170123/（上游原生命名）

$ curl -sS -o libbfio_20170123.orig.tar.gz \
    https://deb.debian.org/debian/pool/main/libb/libbfio/libbfio_20170123.orig.tar.gz
$ sha256sum libbfio_20170123.orig.tar.gz
d45eaa2c7bc5d75905bbd1d04f9730e17bb4b638417343db1af410f3b17a15dd   # 与 .dsc 一致
```

因此 conandata.yml 的 URL/sha256 指向的就是 20170123 这一版的上游内容，
哈希同时锁死内容与版本。Debian 对该包只有二进制构建（.deb），orig 本身
未改动；这属于"权威发行版镜像"口径（档案先例：away 0.9.5 同用
deb.debian.org orig tarball），与 PF7 所拦截的"Debian 重打包"不同。

## 编译步骤

上游发行包自带生成的 configure，树内构建（basic_layout）：

```bash
# 配方 build() 实际序列（内联补丁见下一节）
./configure --enable-static --disable-shared --disable-nls \
            --host=aarch64-unknown-linux-ohos     # 由 AutotoolsToolchain 注入
make -j2
make install
```

## 平台适配（conanfile.py build() 内联，无 patches/ 文件）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type`（config.guess 2015-01-01） | 2017 版 config.guess 不识别 `uname -s = HarmonyOS` | E007：在 `*:NetBSD:*:*)` 前插入 HarmonyOS 分支，映射到 `aarch64-unknown-linux-ohos`（家族先例 libesedb 同法） |
| 2 | config.sub 拒绝 `aarch64-unknown-linux-ohos` | 2017 版 config.sub 无 ohos 识别 | E007：两处锚点——KERNEL-OS 拆分分支 maybe_os 列表加 `linux-ohos*`、os 合法性列表加 `-linux-ohos*`（2017 结构与 2024 不同，libesedb 的三个锚点在本包不存在，不能照抄；补丁后本机验证接受 aarch64-linux-ohos / aarch64-unknown-linux-ohos） |
| 3 | config.status 报 `can't create ./confXXXX/subs1.awk: Permission denied` | HMDFS 上 `umask 077` 建出的 0700 临时目录连创建者都无法写入 | E011：配方只改写 `configure` 内的 2 处 `umask 077`→`022`（源码树内实测就这 2 处）；`config.status` 由改写后的 configure 生成，本包实测无需二次替换（配方不含 config.status 分支） |
| 4 | NLS 依赖 | configure 默认 `USE_NLS=yes`，会探测 gettext | E027：`--disable-nls`，库的 message 翻译功能对 API 无影响，不引入 libintl 依赖 |

依赖注入遵循 R49：无外部依赖，generate() 仅 AutotoolsToolchain 三项参数
（`--enable-static/--disable-shared/--disable-nls`），不注入任何共享前缀。

## 源码修改

无源码文件修改（patches/ 目录为空）。全部平台适配位于 conanfile.py
build() 的内联补丁（config.guess/config.sub/configure），属构建配置层，
不触碰 libbfio 及内嵌 libc* 库的任何 C 源文件。

## 上游测试（R51 三步法）

1. **清点**：tests/Makefile.am 注册的**可执行测试单元 12 个**（计数单位
   =automake 注册项）：`check_PROGRAMS` 10 个测试程序（error、support、
   handle、pool、handle_read、handle_seek、handle_write、pool_read、
   pool_seek、pool_write，L31–L41）+ `TESTS` 2 个测试入口脚本
   （test_library.sh、test_write_functions.sh，L15–L17）。另**单列**
   tests/ 测试源全集 11 个 = 10 程序 + 支持源 `bfio_test_memory.c`
   （无独立入口/无 main，编入 bfio_test_handle 与 bfio_test_pool 的
   SOURCES 提供分配失败注入，L59/L104），不与上表计数混用。
2. **实际运行**（设备原生构建，逐字记录见 `reports/upstream-tests.md`）：
   - **`make check` 原样可跑通**：两个 .sh 入口带 `#!/bin/bash` 而设备无
     `/bin/bash`，用 automake 的 `LOG_COMPILER` 指定一个能力探测通过的
     设备 bash（`/data/service/hnp/bin/bash`，构建目录内 `bash -c pwd`
     rc=0、stderr 空）即可，**上游脚本与 Makefile.am 一个字节未改**；
     `make -j1 check LOG_COMPILER=<bash>` rc=0，`# TOTAL: 2 / # PASS: 2 /
     # FAIL: 0`（E386 的 capability-tested shell 形态）。
   - **上游 `TESTS` 未驱动的 4 个程序**：20170123 版两个 runner 合计只驱动
     10 个程序中的 6 个（test_library.sh 跑 error/support/handle/pool，
     test_write_functions.sh 跑 handle_write/pool_write），
     `handle_read`/`handle_seek`/`pool_read`/`pool_seek` 在 `tests/*.sh`
     中没有任何引用 → `make check` 只编译不执行。按 test_library.sh 的
     `run_test_with_input` 同一调用约定（`<程序> input/raw/test.raw`）补跑，
     4/4 rc=0；10 个程序全量直跑复核同样 10/10 rc=0。
   - `bfio_test_memory.c` 无独立执行形态，其失败注入功能随所编入的
     handle/pool 两程序实跑覆盖。
   - **两个坑（均已绕开，非库缺陷）**：① 无 `/bin/bash`（用 LOG_COMPILER
     指定设备 bash）；② 上游 `test_write_functions.sh` 的 TEST_PREFIX
     推导 sed 比 `test_library.sh` 少一个 `.*$`，在 release/orig tarball
     的顶层目录名 `libbfio-20170123` 下得到 `bfio-20170123`（产物却是
     `bfio_test_*`）→ `Missing test executable: ./bfio-20170123_test_handle_write.exe`；
     该缺陷与平台无关，改用与上游 git 检出等价的目录名 `libbfio/` 运行即通过。
3. **回填**：PR 表格按"automake 注册的可执行测试单元"为单位回填 12/12
   （2 个 TESTS 入口由 `make check` 实跑 + 10 个 check_PROGRAMS 程序全量
   实跑，无跳过、无未执行），与 test_package/MANIFEST.yml、
   reports/test-report.md 同源同单位。

## 验证结果

- conan create（W3，profile ohos-aarch64）：通过，产物 `libbfio.a`
- 消费者 test_package：test_bfio 14 项检查全过（版本串、文件初始化/
  命名/打开/大小/顺序读/内容比对/SEEK_SET/seek 后读/关闭/释放）
- 上游测试：12/12 测试单元覆盖通过（2 个 `TESTS` 入口由 make check 实跑 +
  10 个 `check_PROGRAMS` 程序全量实跑，见 reports/upstream-tests.md）

## 交付物

| 文件 | 说明 |
|------|------|
| libbfio.a | 静态库（--disable-shared，家族口径） |
| include/libbfio.h + libbfio/*.h | 公开头文件（monolithic API + 类型/错误/特性头） |
| pkgconfig/libbfio.pc | 上游 autotools 标准产物 |

库类型包，无可执行文件，不需要 commands.json（R38）。

## 注意事项

- 静态库口径与家族先例（libesedb 20240420）一致：libbfio 非 OHOS 系统
  同名库，但取证库以静态形态消费最稳（无 RPATH/ELF 签名环节）。
- 上游 20170123 之后 API 大改（handle/pool 结构重排），下游 libyal 库
  （libregf/liblnk 等）按同一 2017 API 线依赖本包时，注意以本包
  include/libbfio.h 的 monolithic API 为准。
- L5 基线重立说明：同源码跨轮重验时 `lib/libbfio.a` 字节级不一致
  （ar 归档内嵌构建绝对路径/成员时间戳，每轮验证使用随机命名的私有
  CONAN_HOME，2026-09-18 11:08 轮实测 ~1 差异），按 runtime 判定口径
  删除 reports/baseline.json 重立基线（语义等同首轮）。库为纯静态 .a、
  无 ELF 可执行产物，功能语义两轮一致（W3 消费者 14 项断言两轮全过）。
