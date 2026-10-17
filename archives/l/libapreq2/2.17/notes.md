# libapreq2 2.17 适配笔记

## 编译环境
- 构建系统：autotools（configure + make）
- 编译日期：2026-09-24
- 编译器：clang/clang++
- 状态：built（待 HMBS 真机预检回填实测证据）

## 编译步骤

1. `source()` 下载 `libapreq2-2.17.tar.gz`（archive.apache.org 主源 + downloads.apache.org 回退，同文件同 sha256）与私有 `apr-util-1.6.3.tar.gz`（archive + dlcdn 双官方源，已验证 sha256）。
2. `build()` 先在构建目录完成私有 apr-util 静态子构建：Python 复刻仓内三补丁（E007 `__OHOS__` LIBC、E072 ohos-linux、E011 umask 022），显式 `--build/--host` 绕过旧 config.guess，`--with-apr=<apr-1-config> --with-expat=<expat包>`，安装到构建前缀 `apu/`。
3. 同一阶段写出构建目录假 `apxs`/`httpd` 包装：`apxs -q` 返回私有 apr/apu 路径与 1.7.6/1.6.3 版本，`httpd -v` 返回 Apache/2.4.0，满足 `build/version_check.pl` 探测；`configure` 传 `--with-apache2-apxs=<假apxs> --with-apr-config --with-apu-config --disable-perl-glue`，显式三元组原生构建；configure 内唯一的相对探测 `build/version_check.pl` 改写为源码绝对路径后以 `cwd=build_folder` 异地运行（上游预留 USE_VPATH），`config.status` 的 `./conf*` 落到构建目录。
4. 构建目录运行 `make check` 执行上游 library 套件（见“验证结果”），解析 `library/t/test-suite.log` 的 `# TOTAL/# PASS/# FAIL` 汇总块产生 `HMBS_UPSTREAM_TEST_RESULT`；module 需 live httpd，作为缺口声明不执行。
5. `package()` 在构建目录运行 `make install DESTDIR=<package_folder>`（无 Makefile 才回退源码目录），把私有 `apu/lib/libaprutil-1.a` 合入包内 `lib/`，`package_info.libs` 为 `["apreq2", "aprutil-1"]`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 configure 强制要求 apache2 apxs + httpd 二进制 | `acinclude.m4` 无 apxs 时用 `$APACHE2_APXS -q` 定位 apr/apu，并校验 `$APACHE2_HTTPD -v` 版本 | 构建目录假 apxs/httpd 包装：只满足版本探测，不构建 module/apache2 以外的 httpd 相关产物，perl glue 关闭 |
| 2 | apr-util/1.6.3 仓内无 conan 配方，无法 requires | `archives/a/apr-util/1.6.3` 仅有 manifest/notes/patches，全仓无已发布 apr-util 制品 | 沿用 serf/1.3.10 私有静态子构建：官方双源 + 已验证 sha256，`--with-expat` 外供 expat，产物合入本包 |
| 3 | 旧 config.guess 无法识别 HongMeng 内核 | 2021 版 config.guess 无鸿蒙分支，`checking build system type` 直接失败 | 显式 `--build/--host`（OHOS 用 stock config.sub 可接受的 `*-unknown-linux-gnu`，原生 build==host），保留 config.guess/sub/umask 补丁 |
| 4 | 远端 apr 包重定位后 `apr-1-config --installbuilddir` 返回本机不存在目录 | conan 缓存重定位导致构建期绝对路径失效，apr-util configure 的 `cp apr_rules.mk` 静默失败 | configure 前定位真实 `apr_rules.mk`（优先 `build-1/`），缺失时从校验位置补拷 `build/rules.mk` |
| 6 | 私有 apr-util configure 报 C preprocessor fails sanity check，伴随 configure cd //build-1 | 私有子构建沿用外层工具链 CFLAGS/CPP 且未校验 apr 重定位，预检 configure 在 CPP 检查直接 exit 1 | 移植 serf 私有子构建加固：_tool 探测可用 CC 并固定干净 CFLAGS（-fPIC/-O2，清空陈旧 CPP），CC 目录前置 PATH，mktemp fallback 影子，_resolve 校验 installbuilddir 并在重定位失效时搜索真实 apr_rules.mk，configure 后全树改写 //build-1///include///lib，INSTALL 可用性探测 + 手工兜底，失败转储 config.log 关键段 |
| 7 | 上游 module/t 5 项需 live httpd | `module/Makefile.am run_tests` 经 `Apache::TestMM` 生成 `t/TEST` 并启动 httpd | library 6 项经 `make check` 真跑并以 test-suite.log 为准；module 5 项在标记 gaps 中按 ohos_feature 声明，不计入通过率分子 |
| 8 | 私有 apr-util make 仍调用 `/data/service/hnp/bin/clang` 报 inaccessible（2026-09-24 预检） | 远端 apr 包构建期 CC 烘焙进 apr-util 生成的 Makefile（CC/LIBTOOL 编译参数）；env CC 无法覆盖 Makefile 赋值，configure 后改写仅覆盖 //build-1///include///lib 而遗漏编译器路径 | configure 前记录真实 `apr-1-config --cc` 作为 stale CC，configure 后全树增补 stale CC（含 `/data/service/hnp/bin/clang`）→已探测 CC 改写，并以 `make CC=.. CPP=.. -E` 命令行覆盖编译与安装两步 |
| 9 | apr-util `make install` 与主包 `configure[139]` 报 `/data/service/hnp/bin/bash: inaccessible`（2026-09-24 预检第二轮） | 远端 apr 构建期 SHELL 烘焙为 HNP 绝对 bash；apr-util 编译已过但 cache 内 libtool 以直接执行方式调用该解释器，主包 configure 直接执行同样命中第 139 行 | configure 前后全树改写 `/data/service/hnp/bin/bash`→设备 sh；cache libtool 不就地改，拷贝到构建目录修复 shebang 后重定向 apr-util 生成文件中的 LIBTOOL 引用 |
| 10 | 主包 `configure[139]` 仍报 HNP bash inaccessible，且源码全树改写为 0 文件（2026-09-24 预检第三轮） | 陈旧 bash 不在源文件而在 Conan Autotools 聚合的环境变量中（configure[139] 重 exec $CONFIG_SHELL/$SHELL）；直接执行 `./configure` 必中 127 | 换用与前两轮不同的调用轴：弃用 Autotools.configure 直接执行，改以 `[sh, configure, …]` 显式调用并传入清洗后的环境（全值替换陈旧 bash，SHELL/CONFIG_SHELL 钉为设备 sh）；make/make check 同样走清洗环境手工调用 |
| 11 | 主包 configure 报 `Can't open perl script "build/version_check.pl"` 后 `Bad apache2 binary` 在 configure:13018（2026-09-24 预检第四轮） | libapreq2 的 acinclude.m4 以相对路径 `build/version_check.pl` 探测 httpd 版本，不支持异地构建；`cwd=build_folder` 调用 `<src>/configure` 时该相对路径不存在，版本探测失败连带判假 httpd 为 Bad binary | 改为源码内构建：configure/make/make check 均以 `cwd=source_folder` 运行（`build/version_check.pl` 存在处）；`package()` 同步改到源码目录执行 `make install DESTDIR`（Autotools helper 默认 build 目录为空）；test-suite.log 扫描兼容源码/构建两目录；test_package 改为 StringIO 实采 RESULT 行计数 |
| 12 | 主包 configure 报 `Can't exec .../apu/bin/apu-1-config: Permission denied` 后 `Bad libaprutil version` 在 configure:13089（2026-09-24 预检第五轮） | 手工兜底用 `shutil.copyfile` 拷贝 `apu-1-config`，丢失可执行位；`build/version_check.pl` 以 perl 直接 exec 调用该路径，无 +x 即 Permission denied，版本串为空即判 Bad 版本 | 拷贝后清 HNP 解释器并 `chmod 755`，以直接执行 `--version` 探针验证；若设备 fs 仍拒绝直接执行，回退到 tmpdir 可执行 shim（`exec sh <real> "$@"`，假 apxs 已证明 tmpdir 可执行），`--with-apu-config` 指向可执行路径 |
| 13 | 主包 configure 在 `config.status[1019]` 报 `can't create ./confStKFl8/subs1.awk: Permission denied` 后 `could not setup config files machinery`（2026-09-24 预检第六轮） | 与 apr-util 同源的设备文件系统 mktemp 限制：`config.status` 以 `mktemp -d ./confXXXXXX` 在源码内建临时目录，后续写 `subs1.awk` 无权限；mktemp fallback 影子只加到了 apr-util 的 `env["PATH"]`，主包 `cfg_env` 未复用。`Can't locate Apache/Test.pm` 只是 `acinclude.m4` 中无条件 `HAVE_APACHE_TEST` 探测的 stderr 噪音（`require Apache::Test` 在 version_check.pl:27），非缺依赖 | 主包 `cfg_env` 同样复用 `_mktemp_fallback_shim_for_ohos(tmpdir)` 并前置到 `PATH`（仅当 HMBS 注入 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 时生效，其余 mktemp 委托真实二进制；无注入时行为不变），使 `./conf*` 走 autoconf `mkdir` 回退路径 |
| 14 | 同一指纹第二轮仍报 `can't create ./confQsbfgl/subs1.awk: Permission denied`（2026-09-24 预检第七轮，mktemp 影子已在主包 PATH 仍失败） | 影子只能把 `./conf*` 的 mktemp 转为同目录 `mkdir` 回退，临时目录仍落在源码树内，未换失败轴；且源码内构建把 configure 产物与只读/受限源码目录绑死 | 改换构建目录轴：`_patch_version_check_to_absolute` 把 configure 内唯一的相对探测 `build/version_check.pl` 改写为源码绝对路径（上游已预留 USE_VPATH），configure/make/make check 改以 `cwd=build_folder` 异地运行，`config.status` 的 `./conf*` 落到构建目录；`package()` 改到构建目录执行 `make install DESTDIR`（无 Makefile 才回退源码目录），`test-suite.log` 扫描与 `config.log` 转储兼容两目录，构建前清理构建目录残留 `conf*` |
| 15 | 同一指纹第三轮仍报 `can't create ./confnj3XyS/subs1.awk: Permission denied`（2026-09-24 预检第八轮，cwd=build_folder 仍失败） | build_folder 与 source_folder 同处 conan 缓存同一文件系统（.../b/src vs .../b/build-release），unsafe_local_mktemp 对整个缓存 fs 生效，换目录未换失败轴；HMBS tmpdir 已被 write-probe 与 fake-apxs/apu-shim 直接执行证明可写可执行 | 改换文件系统轴：新增 `_main_build_dir(tmpdir)` 在 HMBS tmpdir 下建 hmbs-libapreq2-build，configure/make/make check 均以该目录为 cwd（保留 version_check 绝对路径补丁与 mktemp 影子），config.status 的 ./conf* 落到可写文件系统；test-suite.log 扫描与 config.log 转储兼容 tmpdir/构建/源码三目录；package() 按 tmpdir→构建→源码顺序找 Makefile 执行 make install |
| 16 | 同一指纹第四轮仍报 `can't create ./conf2mc3lM/subs1.awk: Permission denied`（2026-09-24 预检第九轮，cwd 已是 HMBS tmpdir 仍失败） | 三次换 cwd（源码→构建→tmpdir）指纹不变，失败与位置无关而与模式有关；HMDFS 上 `umask 077` 建出的 conf 临时目录不可再写（darts 联合失败先例），mktemp 影子的 mkdir 回退继承同一 umask；主包 configure 从未做 apr-util 已有的 umask 改写 | 改换模式轴：新增 `_patch_main_umask_for_hmdfs` 把主包 configure 模板内 `umask 077` 改写为 `umask 022`（覆盖生成的 config.status），保留 tmpdir cwd、version_check 绝对路径与 mktemp 影子 |
| 17 | 同一指纹第五轮预期：umask 022 + tmpdir cwd + mktemp 影子仍无法换轴（第三策略周期首轮，2026-09-24） | 重读 DRAFT-6507（cln/1.3.7 同指纹实证）：GNU `mktemp -d` 恒以 0700 建目录、不经 umask，故 022 改写对 mktemp 主路径无效；影子依赖 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 注入，未注入即无 fallback；三次 cwd 指纹不变已证失败与位置无关 | 改换创建原语轴：`_patch_main_umask_for_hmdfs` 改为放弃 mktemp——把 configure 模板内 `mktemp -d "./confXXXXXX"` 改写为 `false` 强制走 autoconf `mkdir` 回退，并仅把该回退的 `(umask 077 && mkdir` 放宽为 `(umask 000 && mkdir`（0777，cln 定型方案）；保留 tmpdir cwd 与 version_check 绝对路径，不依赖注入标志 |

## 源码修改

无。上游 2.17 已兼容当前工具链预期，`conandata.yml` 无 patches；apr-util 子构建的 OHOS 补丁在 `build()` 内以 Python 字符串改写完成，不落补丁文件。

## 依赖版本

- apr/1.7.6（直连；远端已发布，为私有 apr-util 子构建与主构建提供 apr-1-config）
- expat/2.8.2（直连；已发布，供私有 apr-util `--with-expat`；apr-util 1.6.x 已无 bundled expat）
- apr-util/1.6.3（私有静态子构建：官方源码包 + 已验证 sha256，不走远端 requires；产物 libaprutil-1.a 合入本包 lib/）

## 验证结果

```bash
# HMBS 真机预检（conan create）待运行；通过后回填：
# - make check：library/t 6 项（version/cookie/params/parsers/error/util），以 test-suite.log 为准
# - test_package ./test_apreq2：2 项（version_string + cookie_parse）
# HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 以预检 stdout 实测为准
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libapreq2.a（默认）或 lib/libapreq2.so | 静态/共享库（二选一，随 shared 选项） |
| lib/libaprutil-1.a | 私有 apr-util 静态归档（随包发布，供链接） |
| include/apreq2/*.h | 公共头文件 |
| bin/apreq2-config | 上游配置脚本 |

## 注意事项

- 默认静态构建（`shared=False`）；package 阶段裁剪未选链接形态时保留私有 `libaprutil-1.a`。
- 上游已归档只读（Apache 宣布退役），2.17 为既定适配版本，不追踪 trunk 2.18。
- 真机与命令属于内部基建，不写入 PR 正文；正文统一写“在 HarmonyOS aarch64 环境实测”。

| 22 | 主包 `make` 在 `module/apache2/handle.c:18` 报 `fatal error: 'httpd.h' file not found`（2026-09-26 预检；library/ 已编过，卡在 module/apache2） | 上游顶层 `SUBDIRS` 恒含 `module`（`module/SUBDIRS=apache2`，`module/apache2/Makefile.am` 无条件编 `mod_apreq2.la`），`APACHE2_INCLUDES=-I<apxs -q INCLUDEDIR>`；假 apxs 为通过 `version_check.pl` 把 INCLUDEDIR 应答为 apr 头目录，其中无 httpd.h，而 OHOS 仓内无 httpd 配方 | 新增 `_drop_httpd_module`：configure 通过后（探测已过）把生成态顶层 Makefile 的 `SUBDIRS` 去掉 `module`（另清空 `module/Makefile` 的 apache2 子目录兜底），只构建可移植的 `library/libapreq2.la` + `include/` + `apreq2-config`；apache2 filter 与 module/t 5 项同属无 httpd 缺口，已在标记 gaps 声明 |

| 23 | 去 httpd 后 `make check` 返回 0 但无 `test-suite.log`（marker executed=0），且 `package()` 在 include/ 报 `install-pkgincludeHEADERS Error 64`（2026-09-26 预检第二轮；compile 已过） | `library/Makefile.am` 无 `SUBDIRS` 条目，automake `check-recursive` 永不进入 `library/t/`（其 Makefile 仍经 AC_CONFIG_FILES 生成；上游经自定义 `make test` 链跑 perl harness，不产 test-suite.log）；顶层 `make check` 故恒为空跑。Error 64 为 configure 烘焙的 INSTALL 程序在设备上用法错误（与私有 apr-util 安装阶段同轴） | 与上轮换轴：不再改构建图，改调用与安装环境——`build()` 在顶层 check 后显式到 VPATH `library/t` 再跑一次 `make check`（automake harness 写 test-suite.log，失败只 warn、标记如实）；`package()` 复用 `_probe_usable_install` 探测并显式传 `INSTALL=<可用> -c` + `MKDIR_P=mkdir -p`，另兜底重调 `_drop_httpd_module`；`_parse_automake_log` 的 not-found reason 附被搜目录以便下轮定位 |

| 24 | `library/t` 链接报 `undefined symbol: apreq_version_string/version` 且前有 `src/apreq2-config: inaccessible`，`package()` 仍 `install-pkgincludeHEADERS Error 64`（2026-09-26 预检第三轮） | `acinclude.m4` 中 `APREQ_CONFIG="$top_builddir/apreq2-config"` 且 `top_builddir="$abs_srcdir"`，而 `AC_CONFIG_FILES([apreq2-config])` 写到 builddir；VPATH 下 Makefiles 烘焙的 srcdir 路径永不存在（`AM_LDFLAGS=\`@APREQ_CONFIG@ --link-libtool --libs\`` 在 library/t/Makefile.am），LDFLAGS 为空即缺 -lapreq2。Error 64 是单文件探针通过但多文件 `-m 644`/`-d` 面失败：设备 install 不支持完整 GNU 参数面 | 新增 `_repair_apreq_config_vpath`：configure 后把 builddir 生成的 `apreq2-config` 镜像到 srcdir 路径（双向兜底）、清 HNP 解释器、`chmod 755`、直接执行 `--libs` 探针；build() 在 libtool 重定向后调用。新增 `_write_install_wrapper`：POSIX `cp/mkdir/chmod` 实现 `-c/-m/-d/-t/-D` 与单/多文件拷贝，四种 automake 模式探针通过才用；`package()` 优先 wrapper、回退可用系统 install |

| 25 | `library/t` 链接报 `cannot find the library '.../b/src/library/libapreq2.la'`，`make check` 无 test-suite.log（2026-09-26 预检第四轮） | 同 #24 的 VPATH 轴：`top_builddir="$abs_srcdir"` 使 library/t Makefile 烘焙 srcdir 绝对路径，而构建产物在 builddir `library/libapreq2.la` + `.libs/`；apreq2-config 镜像只修了 LDFLAGS，未修 libtool 输入路径 | 新增 `_mirror_library_la_for_vpath`：configure 后与主 make 后各镜像一次，把 builddir `library/libapreq2.la` 拷贝到 srcdir 同路径并整树拷贝 `.libs/`；缺构建产物时 warn 跳过、不造 stub |

| 26 | test_package CMake 报 `CMAKE_C_COMPILER: /data/service/hnp/bin/clang is not able to compile`（2026-09-26 预检第四轮同轮） | profile/conf 的编译器路径烘焙自远端 apr 构建主机，在真机不可执行；test_package 原 generate 直接用默认工具链，未做可用性探测 | test_package 新增 `_usable_compiler`：`--version` 实测 conf 编译器，不可用则回退 PATH 的 clang/cc/gcc，写入 `tc.cache_variables` 并按 zydis/4.1.1 经验回写 conan_toolchain.cmake + 导出 CC/CXX 构建环境 |

| 27 | `library/t` 的 `make check` 在 version.t.log 报 TAP Harness Error 2 且无 test-suite.log（2026-09-25 预检本轮；6 个 C 程序均已编过） | 上游 library/t/Makefile.am 的 `TESTS_ENVIRONMENT = @PERL@ -MTest::Harness ...` 为串行 harness 而写（`make test` 直调 .t 包装）；并行 harness 下每项以 `$(TESTS_ENVIRONMENT) $(LOG_DRIVER) --test-name ...` 运行，perl harness 被要求把 `/bin/sh test-driver ...` 当用例执行，零 TAP 即 Error 2；且标记缺 gaps（executed=0 无缺口声明） | library/t 的 `make check` 追加 `TESTS_ENVIRONMENT=` 清空（.t 包装 `#!perl` 实为 sh 注释+`exec './binary'`，test-driver 直接执行可采 TAP 并写 test-suite.log）；标记 discovered 锚定审计总数 11（library 6+module 5），skipped=11-executed，状态按 failed>0→failed、executed<11→incomplete、否则passed 三分支，gaps 固定 5 项 ohos_feature（module/t 需 live httpd），失败路径同样带 gaps+reason |

| 28 | 上轮清空后 `make check` 报 `src/test-driver: No such file` Error 127 且标记 gaps 仅 5 项被判缺口不足 11（2026-09-25 预检本轮） | 与上轮不同轴：tarball 从未发布 test-driver（上游只用串行 `make test`，从不用并行 check），清空后并行 harness 无 driver 可调；且失败分支 gaps 仅声明 module 5 项，executed=0 时实际缺口为 11（6 library 未执行+5 module） | 改走上游原生串行链：`make check` 仅 warn-only 保障 check_PROGRAMS 编出，新增 `_run_library_make_test` 跑上游 `make test` 并落盘 hmbs-make-test.log（含逐二进制 TAP 非空证伪），`_parse_make_test_log` 按 `*.t .. ok/not ok` 逐行定程序级 executed/passed/failed；标记单源优先 test-suite.log、回退 make-test.log（command 如实为 make test），失败分支 gaps 补为 6 项 test_failure+5 项 ohos_feature 合计 11 |

| 19 | 源码获取阶段 `Signal 9` + `gzip: stdin: unexpected end of file`（2026-09-25 预检，compile 阶段无配方输出） | 外部 gzip/tar 管道解包截断归档：conan `get()` 先流式解包后校验，截断下载在外部 gzip 直接 EOF + 进程被杀；且仅有两个官方源无国内回退 | `conandata.yml` 两归档各补 tuna/aliyun/ustc Apache 镜像并保留官方回退（同 sha256）；`source()` 改纯 Python（urllib 按序下载到暂存文件、sha256 先验后用 tarfile 解包并手动 strip_root），截断变为可重试的下载错误，不再进 gzip 管道 |

| 20 | 裸 `Signal 9` 且 stdout/stderr 为空（2026-09-25 预检第二轮；上一轮下载加固后 gzip 报错消失、Signal 9 指纹仍在） | 与上一轮不同轴：下载截断已排除，空日志说明 kill 发生在配方进度输出之前，私有 apr-util 目标文件与主构建树峰值磁盘占用为剩余嫌疑 | 新增纯 stdlib `_log_resource` 在 source/build/apr-util 阶段边界打 HMBS-PROGRESS 与剩余磁盘快照以定位 kill 点；私有 apr-util 安装成功后 best-effort `make clean` 释放目标文件，不动下载 URL 逻辑 |
| 21 | 国内 apache 镜像 404 + `_patch_apr_util` 因 `build/config.guess` 缺失崩溃（2026-09-25 预检第三轮；tuna/aliyun/ustc 对两归档均 404 后回退 archive 成功，但 build 仍 FileNotFoundError） | libapreq2 已退役仅 Archive 有包、apr-util-1.6.3 已被镜像上的 1.6.5 取代，国内镜像无归档文件；补丁把 best-effort 改写做成硬失败，缺文件即崩 | `conandata.yml` 删除 tuna/aliyun/ustc 三镜像、只保留官方 archive/downloads/dlcdn（同 sha256，archive 实测可达在前）；`_patch_apr_util` 改为缺文件 warn 跳过（显式 --build/--host 已绕过旧 config.guess），aux 文件兼容 build/ 与顶层两种布局并打印 src 布局快照 || 18 | \u4e3b\u5305\u7f16\u8bd1\u9636\u6bb5\u88f8 Signal 9 \u4e14 stdout/stderr \u5c3e\u90e8\u4e3a\u7a7a\uFF082026-09-25 \u9884\u68c0\uFF09 | \u65e0 config.log/\u6784\u5efa\u8fdb\u5ea6\uFF0C\u6740\u8fdb\u7a0b\u53d1\u751f\u5728\u4efb\u4f55\u914d\u65b9\u8f93\u51fa\u524D\uFF1BTMPDIR \u5b50\u76ee\u5f55\u6784\u5efa\u4e24\u5957\u5b8c\u6574 autotools \u6811\uFF08\u79c1\u6709 apr-util + \u4e3b\u5305 VPATH\uFF09\u53ef\u80fd\u585e\u6ee1\u8f83\u5c0f tmpfs \u5bfc\u81f4 OOM/SIGKILL | \u4e3b\u6784\u5efa cwd \u8fd4\u56de build_folder\uFF08\u5927\u5206\u533a conan \u7f13\u5b58\uFF09\uFF0C\u4fdd\u7559 mktemp->false + umask 000 \u7684\u6587\u4ef6\u7cfb\u7edf\u65e0\u5173\u4fee\u590d\uFF1B\u589e\u52a0 HMBS-PROGRESS \u8fdb\u5ea6\u6807\u8bb0\u4fbf\u4e0b\u8f6e\u5b9a\u4f4d\uFF0C\u6811\u904d\u8d70\u88c1\u526a .git \u964d\u4f4e\u8bbe\u5907\u8d1f\u8f7d |\n\n
| 29 | 人工审查打回 rule4：上游 11 项 0 执行（2026-09-26，PR #12806 评论 #191714214）| 前序 _drop_httpd_module 把顶层 SUBDIRS 的 module 整体去掉，连不依赖 httpd.h 的 module/test_cgi（5 个 module/t perl 测试经 HTTP 驱动的同一 CGI 二进制）也永不构建；且 library 6 项完全依赖 perl Test::Harness 日志，设备缺 perl 即 executed=0 | _drop_httpd_module 改为只清空 module/Makefile 的 apache2 子目录、保留顶层 module，使 make 在 module/ 仍编出 test_cgi；build() 新增 _build_module_test_cgi + _run_module_cgi_direct（上游 test_cgi 直调 CGI env/标准输入，5 个 CASE 行 1:1 对应 big_request/cgi/cookie/request/upload 的 .t 断言，先探 perl Apache::Test 再回退 CGI 直跑，输出非空+模式双断言防空夹具），新增 _write_direct_tap_log/_parse_direct_tap_log（6 二进制直跑 TAP，plan+not ok+exit 三条件，无字符串计数修补）；_emit_upstream_marker 改为 library（test-suite.log>make-test.log>direct TAP）+ module（CASE）组合计数，discovered=11，gaps 仅对真实未执行项声明 | 
| 30 | 人工审查打回 rule4：上游 11 项 0 执行（2026-09-28，PR #12806 评论 #191856673）| 落地 row 29 方案时发现工作树 conanfile.py 实际仍是旧逻辑：顶层 SUBDIRS 去掉整个 module（test_cgi 永不构建），_emit_upstream_marker 只有 library 三级回退且 module 5 项恒为 ohos_feature gaps 声明、无任何真实执行，故预检 marker executed=0 | 本轮实际修改工作树：① _drop_httpd_module 不再动顶层 SUBDIRS（仅探活 module 条目），只清空 module/Makefile 的 apache2 子目录（build/source 双树）；② 新增 _write_direct_tap_log/_parse_direct_tap_log（无 perl 回退：.t 系 `#!perl`+`exec './binary'` 生成，C 二进制直跑即上游测试本体，exit 0+非空+`1..N` plan+零 `not ok` 四条件）；③ 新增 _build_module_test_cgi（module/ 目录显式 make，定位 test_cgi，不造 stub）+ _run_module_cgi_direct/_parse_module_cgi_log（5 CASE 行，输入/期望逐字取自 5 个 .t：big_request 长查询计数分支、cgi `foo=%3F&bar=hello+world`、cookie netscape `apache=ok`、request `test=1` 同 parse 路径计数分支、upload `foo=0`+cgi.t filler POST；先探 `perl -MApache::Test`，HTTP 驱动需 live httpd 故执行器恒为 CGI 直调）；④ _emit_upstream_marker 改为 library 单源优先级 + module CASE 组合计数（discovered=11，gaps 只对真实未执行子集声明，全执行时无 gaps）；⑤ 同步 pr-body.md 执行方式描述与 notes 本行 |
| 31 | 2026-09-28 预检上游 11 项全执行全失败：direct TAP 六项 exit=127，CGI-direct 五项 not ok，且 marker 无 gaps 被 rule4 判缺口不足 | 并行 make check 需要 tarball 从未发布的 test-driver（上游只用串行 make test）；直跑二进制用裸 env，共享依赖库目录不在 loader 路径；marker 只对未执行项声明 gaps，全执行全失败时缺口为零 | 本轮工作树修改： library/t 不再调用并行 make check，改为 make check_PROGRAMS 只构建二进制再走上游 make test；新增运行时 env（apr/expat/apu 及 .libs 入 LD_LIBRARY_PATH）与 libtool 包装容错（126/127 时经 sh 重试），直跑 TAP 与 CGI-direct 共用；marker 对已执行未通过项补 test_failure gaps，缺口总数恒等于总数减通过数；直跑日志新增二进制种类与 loader 路径诊断行 |
