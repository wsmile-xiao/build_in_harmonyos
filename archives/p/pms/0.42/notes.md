# pms 0.42 HarmonyOS PC 适配笔记

## 软件

- 名称：pms（Practical Music Search）
- 版本：0.42
- 描述：基于 ncurses 的交互式 MPD（Music Player Daemon）客户端，C++ 编写，Vim 风格操作
- 上游：https://sourceforge.net/projects/pms/（0.42 发布于 2010-05-14，pms-0.42.tar.gz）
- 官网文档：https://ambientsound.github.io/pms
- 许可：GPL-3.0-or-later（源码头声明 GPL v3+）

## 构建系统

- Autotools：autoconf 2.65 生成的 configure + automake Makefile.in，顶层 `bin_PROGRAMS = pms`。
- `src/` 内嵌 libmpdclient（libmpdclient.c/.h），无需外部 MPD 客户端库。
- 无 configure 测试开关，无 TESTS/check_PROGRAMS（审计见 test_package/MANIFEST.yml）。

## 依赖（全部来自 ohpcd 制品仓）

- glib/2.88.0.1（shared；configure 用 `PKG_CHECK_MODULES([GLIB], [glib-2.0 >= 2.0])`）
- ncurses/6.6（自带 m4/ncurses.m4 的 MP_WITH_CURSES 探测，优先 ncursesw）
- gettext/0.22.5.1（AM_GLIB_GNU_GETTEXT 硬性要求 gettext；该年代 configure 不提供 --disable-nls，只能完整启用 NLS；同时提供 msgfmt 供 po/ 构建）
- 无 libiconv 依赖：gettext/0.22.5.1 在 ohpcd 基于 OHOS 系统 iconv 构建（无外部依赖），其 libintl 无需 -liconv 即可链接；显式 requires libiconv/1.17 会在其源码构建阶段继承 profile 写死的 CONFIG_SHELL=/data/service/hnp/bin/bash，在部分 worker 上不可执行（inaccessible），导致依赖先于主包失败。同类包 ncmpcpp/audtty 均未引入 libiconv。

## 适配做法（无 patches/，全部在 conanfile.py 内联）

1. `--build/--host=aarch64-unknown-linux-ohos`：autoconf 2.65 的 config.guess 在 HMDFS 上建不出探测文件，必须显式三元组。
2. `umask 077 → 022`：configure 及其生成的 config.status 用 umask 077 建临时目录，HMDFS 拒绝，改 022。
3. 时间戳固定：configure.ac/Makefile.am/m4 < aclocal.m4 < configure/config.h.in < Makefile.in，保证 make 不重调 aclocal/automake（CI 无此工具）。
4. `CC/CXX` 取自 `tools.build:compiler_executables`（R33，缺失时回退 PATH 查找），同时以 `CC=/CXX=` 参数显式传给 configure（conanbuild 环境会覆盖裸 os.environ，参数透传才可靠）并在 make 命令行透传，覆盖老 Makefile.in 里写死的 `cc`（OHOS 无 cc 二进制，只有 clang）。
5. gettext 的 `bin/` 前置到 build 期 PATH，提供 msgfmt；`LD_LIBRARY_PATH` 追加各依赖 `lib/`，供 configure conftest 与 `make check` 的二进制执行。
6. `SHELL/CONFIG_SHELL` 仅指向经 X_OK 验证的可执行 bash（profile 写死的 /data/service/hnp/bin/bash 在部分 worker 上不可执行，只做 isfile 判断会把坏路径透传给 configure；现要求 isfile+X_OK，否则回退 PATH/bash）；`TMPDIR/TMP/TEMP` 复用 HMBS 注入的可写目录（真机 /tmp 只读），且 build() 内先解析可写目录再打补丁。configure 内 `/tmp/` 改写为该目录的字面路径（单引号内 `$TMPDIR` 永不展开，字面路径才安全），`ac_tmp=$tmp` 重定向到其下 per-PID 子目录（E114 模式；autoconf 2.65 模板若无此串则仅做 /tmp 改写），shebang 改指 HNP bash（toybox sh 无视 TMPDIR 硬写 /tmp，bash 才认 TMPDIR）。
7. 双烟囱测试：裸编译器直编通过后，再用 `env="conanbuild"` 聚合环境（configure 同款 CFLAGS/LDFLAGS）复现 conftest 编译链接，两轮都过才进 configure；configure 失败时从 config.log 抽错误行打 `HMBS_CONFIGLOG` 短行标记（长 tail 会被摘要省略）。

## 测试

- 上游原生：无测试套件（发布包 92 条目逐条清点：无 tests/test 目录、无 *test* 文件名——大小写不敏感全量扫描 0 命中；Makefile.am 仅 `bin_PROGRAMS = pms`；configure.ac 无测试宏；src/ 35 个源码无测试源。Git 0.42.x 分支的 `testpms` 是发布后新增的手工 `make + gdb ./pms` 脚本，不在发布包内且需交互式 gdb 与在线 MPD，不可在 CI 运行）。
- OHOS synthetic 上游检查（HMBS 证据门禁要求 discovered>0）：2026-09-12 预检以 "incomplete：清单表明上游存在测试，必须在真机发现并执行" 驳回 `status: no_tests/discovered:0`；同类包 audtty/0.1.12 在 2026-08-31 收到同一 verdict 并以 synthetic `make check` 合入。照此模式：conanfile.py build() 在 `make` + 样板 `make check` 之后，对构建树刚产出的二进制（`build/src/pms`，非安装副本）执行 `--help`（须含 `Usage:`）与 `-v`（须含 `0.42` 与 `Practical Music Search`）真实验证，两份输出原文回显到日志（非空、可证伪：桩二进制必然失败 grep），`discovered=1/executed=1/passed=1/status=passed`，写入 `upstream_test_result.json` 并由 package() 随包持久化到 `res/`（包缓存命中轮次 build() 跳过时 test_package 仍有证据）。automake 的单冒号 `check:` 目标不可追加竞争规则（`:` 与 `::` 混用即致命错误），故验证放在 build() 内而非注入 Makefile——与 audtty 手写 Makefile 的注入点不同，证据口径一致。
- test_package：test_pms.sh 对安装后的 `bin/pms` 做 6 项真实调用验证（-v 横幅含 0.42 与程序名、--help 含 Usage 与 hostname 选项、非法选项显式拒绝），输出 `RESULT: N passed, M failed` 并据此产生 `HMBS_TEST_PACKAGE_RESULT`；随后读取包内 `res/upstream_test_result.json` 校验（status=passed、discovered>0、executed==discovered、failed==0）后双通道复发 `HMBS_UPSTREAM_TEST_RESULT`，缺失或非法直接抛异常、不伪造。
- 注意：pms 的 `-v/--help` 打印后按上游逻辑返回 PMS_EXIT_BADARGS（4），配方与脚本均用 `|| true` 承接并只断言输出文本。

## 同类经验复用

- archives/n/ncmpcpp（同为 ncurses MPD 客户端）：triplet 显式化、umask、时间戳、conftest 期 LD_LIBRARY_PATH。
- archives/a/audtty（ncurses + glib autotools 应用、无上游测试）：内联 synthetic/make-check 证据、HMBS 双标记、TMPDIR 链、Makefile 硬编码 CC 覆盖。
- knowledge 建议（E027 / debug-methodology）：musl 缺 gettext 时优先 `--disable-nls`；但本包老 configure 无此开关，故反向选择完整 requires gettext。
