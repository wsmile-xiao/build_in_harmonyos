# libextractor 1.17 适配笔记

## 编译环境
- 构建系统: autotools（官方发行归档含预生成 configure，无需 autogen）
- 编译日期: 2026-09-18
- 编译器: clang 15（HarmonyOS PC 真机原生，非交叉）
- 状态: built（待真机预检）

## 编译步骤

```bash
conan create archives/l/libextractor/1.17 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

关键 configure 传参：`--disable-nls --disable-glib --enable-shared
--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
（`--without-ffmpeg` 经 configure 证实为无法识别选项，已移除；ffmpeg/gstreamer 本就随缺失依赖自动关闭）。
构建后同一目录执行 `make check` 运行上游测试并输出
`HMBS_UPSTREAM_TEST_RESULT` 标记；随后 test_package 直接调用经
`--version` 探针选出的真实编译器编译 test.c（`test_type=explicit`，
无 CMake 生成器），运行产物并输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 OHOS 三元组 | 上游 config.guess/config.sub 无 ohos 条目 | configure 显式传 `--build/--host=aarch64-unknown-linux-ohos`，并在 conanfile 内对 config.sub 做 ohos 识别补丁（lvm2/util-linux 先例） |
| 2 | configure 临时目录在只读 /tmp 失败 | OHOS /tmp 只读，mktemp 默认 umask 077 | configure 内 `umask 077` 改 `umask 000`（E011），并导出 `TMPDIR=<build_folder>` |
| 3 | 可选依赖（gtk/glib/gstreamer/ffmpeg 等）在 OHOS 缺失 | 上游全部可选，缺失应自动降级 | 显式 `--disable-nls --disable-glib` 确定性关闭（`--without-ffmpeg` 非法，已删；ffmpeg 随依赖缺失自动关闭），其余缺失自动降级；仅保留 zlib/bzip2/libtool 三个制品仓已有依赖 |
| 4 | 插件必须为共享模块 | libtool 插件经 ltdl 动态加载，`--disable-shared` 会导致加载类测试失败 | 默认 `shared=True` 并传 `--enable-shared` |
| 5 | `secure_getenv` 未声明致 `extractor_plugpath.c:482` 编译失败 | 1.17 经 `#if _GNU_SOURCE`（config.h 强制 `_GNU_SOURCE=1`）无条件选用 `secure_getenv`，OHOS libc 无此函数，clang 报隐式声明 + int-conversion 错误；上游 1.18（commit 51c0610a，gnunet#11609）已改为 `#ifdef HAVE_SECURE_GETENV` + getenv 回退 | conanfile 内幂等原地编辑回移植上游 1.18 块（`HAVE_SECURE_GETENV`→secure_getenv；WINDOWS→getenv；`HAVE_ISSETUGID`→issetugid；否则 getuid/geteuid/getgid/getegid 回退），与上游 master 逐字一致，无静态补丁文件 |
| 6 | `package()` 全量 `make install` 时插件 relink 报 `ld.lld: unable to find library -lextractor_common`（libextractor_odf.la，2026-09-19 预检） | libtool DESTDIR 分阶段安装：插件以 `-L<DESTDIR>/lib -lextractor_common` 重链接，要求 src/common 的 libextractor_common.la（`lib_LTLIBRARIES`，插件经 `../../src/common/libextractor_common.la` 依赖它）已先装入 staging；顶层一次安装时序无保证 | package() 第二轮改用 `_prestage_dependency_libs`：先 `make -C src/common/src/main install DESTDIR=<pkg> -j1` 预装依赖库（幂等），再校验 staging 内 `libextractor_common.so` 链接名存在（缺失则由版本化 .so 建 symlink，失败则复制兜底），最后全量 `make install -j1`；同时输出 staging libdir 清单供下轮取证（该轮预检仍在同一 relink 点失败） |
| 7 | 第二轮子目录预装（`make -C src/common install`）后仍在同一插件 relink 点失败 | 子目录 make 在 package() 上下文中的行为未经证实（预检摘要未收录预装成功/失败日志行），且单次全量安装的串行 SUBDIRS 顺序（include→main→common→plugins）本就应先装入 common，失败点不变说明需换策略 | 第三轮改用全量安装两遍重试 `_install_with_retry`：不再调用子目录 make；第一遍失败后必然已装入 common（串行顺序保证），补齐 dev 链接名并输出 staging 清单后原样重跑全量 `make install -j1`，使插件 relink 解析到已装入的库；第二遍失败则带 staging 清单上抛 |
| 8 | `package()` DESTDIR relink `-lextractor_common` (odf, 2026-09-19) | Conan --prefix=/ + DESTDIR staging: plugin relink needs staged `libextractor_common.so` dev link; serial SUBDIRS already installs common first yet second full-pass retry still failed, so timing/order was wrong hypothesis; build-tree `.libs` links fine (make ok, only install fails) | generate() appends build-tree `-L<build>/build-release/src/common/.libs -L<build>/src/common/.libs` (+main) via `tc.extra_ldflags`, package() single `make install -j1` without retry/subdir-make; relink resolves same SONAME from .libs; staging only logged |
| 9 | test_package `cmake.configure()` 失败 (2026-09-19 预检): `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 无法编译简单测试程序 + `System is unknown to cmake, Platform/HarmonyOS` | CMakeToolchain 把 profile `tools.build:compiler_executables` 的绝对路径原样写入 toolchain，主配方侧的 CC 探针/SHELL 修复影响不到它；该路径在预检机上不存在（真机编译器为 harmonybrew clang），且 stock cmake 无 HarmonyOS 平台模块 | test_package 去掉 CMake（删 CMakeLists.txt 与 CMakeDeps/CMakeToolchain 生成器），改直调 `--version` 探活编译器编译 test.c，链接标志从 Conan 依赖元数据拼装（acsccid 先例）；test() 经 subprocess 捕获输出，按 `^check N passed` 行计数出标记，rc=0 但行数不足判为静默跳过而非通过 |
| 10 | compile 阶段 `sh: /storage/Users/currentUser/.harmonybrew/bin/rm: Operation not permitted` (2026-09-20 预检) | PATH 首位 harmonybrew/bin 内 rm shim 不可执行（EPERM）；configure/make 的裸 `rm` 经 PATH 解析到该路径后 exec 失败 | 新增 `_resolve_working_rm()` 实测探活（`rm --version` 能 launch 即可用，OSError 跳过），优先选用 /bin/rm；在 generate()/build()/package() 导出 RM 并把其目录前置到 PATH 首位，harmonybrew 保留供 clang 发现；不跳过任何测试 |
| 11 | compile 阶段 Signal 9、无输出终止 + 本地 conanfile.py 语法损坏 (2026-09-20 预检) | 真机摘要仅 `Signal 9` 且 stdout/stderr 为空，符合小内存盒 OOM 特征；本地 `_fix_libtool_rm_flag` 上轮编辑截断，`re.sub` 行未闭合导致后续函数体错位合并，`py_compile` 报错，且 `_repair_generated_shell_refs` 无大小守卫逐文件读全量 build 树会放大峰值内存 | 1) 补全 `_fix_libtool_rm_flag` 为双模式 `RM` 到 `rm -f` 的幂等重写（覆盖 libtool+Makefile，超 1MB 跳过），删除截断残留的重复尾部，`py_compile` 通过；2) 降峰值内存：`tc.extra_cflags/cxxflags` 追加 `-O1 -g0`，头文件仍由 AutotoolsDeps 提供，`-j1` 与仅关闭 nls/glib/ffmpeg 探测开关不变；3) shell 修复跳过二进制扩展名与超 512KB 文件；不跳过任何测试 |
| 12 | `make check` 在 doc 子目录失败：`doc/libextractor.info Error 1`（`version.texi:35 unknown command '('` + `@subtitle` 警告，真机 makeinfo 与上游 texi 不兼容，随后 toybox `mv: bad '.amXXXX/libextractor.info'`），顶层 `check-recursive Error 1`，上游测试标记 failed（2026-09-20 预检） | 文档工具链问题，非库功能/测试失败；`make -j1` 本体已成功；`make install` 同样会触发该 info 规则（此前被 odf relink 失败掩盖，未走到 doc） | conanfile 新增 `_neutralize_doc_info_build()`：configure 之后把所有 doc 目录的 `libextractor.info*` touch 到最新（缺失则建最小占位），使其新于 `version.texi/libextractor.texi`，make 直接判定 up-to-date 跳过 makeinfo；check 与 install 同治；不改任何 .texi 源码与测试 |
| 13 | 同轮 `src/main` 的 test_file/test_gzip/test_bzip2 全部 SKIP（exit 77），executed 0 | 上游源码 `if (0 != access("test_file.dat[.gz/.bz2]", R_OK)) return 77;`：fixture 只在源码 `src/main` 存在，VPATH 构建目录（`build-release/src/main`）CWD 下缺失即跳过；属构建目录缺文件，非功能缺失 | 新增 `_stage_check_fixtures()`：check 前把 `test_file.dat(.gz/.bz2)` 从源码树复制到每个缺失的已配置 `src/main` 构建目录（仅补齐上游 in-source 构建本就有的 CWD 文件，不改断言）；缺源文件则大声记录 |
| 14 | 上轮 `_neutralize_doc_info_build()` 在 `make -j1` 之前 touch（touched=1），但同条 doc info 规则在 `make check` 仍触发失败；上游 52 个测试已全部通过（`discovered/executed/passed=52`，含 src/plugins 约 45 项），仅 doc 环节拖死整个 check（2026-09-20 第二轮预检） | 时序竞态：automake stamp-vti 流程在 `make all` 期间刷新 `version.texi`，使之前 touch 的 `.info` 重新变旧，`make check` 再次触发 broken makeinfo；touch 本身找对了文件（touched=1），只是时机早了 | 改换时序策略（与上轮不同）：`_neutralize_doc_info_build()` 改到 `make -j1` 之后、`make check` 之前调用，并在 `package()` 的 `make install` 之前再调一次（install 触发同一规则）；方法内新增 mtime 校验日志（`doc info fresh: info_newest vs texi_newest ok=`），下轮可直接验证；另把 MANIFEST 的 `upstream_test_total` 7→52（本次配置下 automake 实际注册总数，证据即 marker）、`assertion_count` 11→56 |

## 源码修改

无静态补丁文件（patches/ 为空）。全部平台修正通过 configure 传参 + conanfile 内
config.sub/configure 文本补丁完成，未改上游功能源码；另有 `src/main/extractor_plugpath.c`
的程序化原地编辑（回移植上游 1.18 的 `secure_getenv`→`getenv` 可移植分支，与上游
master 逐字一致，幂等、无静态 patch 文件，锚点缺失时大声失败）。

## 依赖版本

- zlib/1.3.1（已发布，gzip 容器测试需要）
- bzip2/1.0.8（已发布，bzip2 容器测试需要）
- libtool/2.5.4.1（提供 libltdl 插件加载运行时）

## 验证结果

待 HMBS 真机预检返回后填写：

```bash
# 上游测试：make check（src/main，见 test_package/MANIFEST.yml 的 7 项登记）
# test_package：直调编译器编译 test.c 后运行 ./test_libextractor（4 断言）
```

- 上游测试用例数：src/main 共 7 项（5 基础 + test_gzip + test_bzip2），来源 src/main/Makefile.am 的 check_PROGRAMS/TESTS
- 新增测试用例数：test.c 共 4 断言（plugin defaults、metatype 字符串、版本宏、extract 配置路径）
- 证伪要求：确认 test-suite.log 非空且含 7 项 PASS；必要时以失败桩验证 harness 可捕获失败；区分通过与静默跳过（exit 77 记为跳过，不计通过）

## 注意事项

- 上游 1.17 发布于 2026-07-05，源码包 8309829 字节，sha256 与 Debian .orig 一致
- 官方原始 URL 保留在 conandata.yml 最后作为回退，国内镜像在前
- PR 正文不写真机 IP/命令细节，统一写「在 HarmonyOS aarch64 环境实测」
