# aribb24 1.0.4 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am, LT_INIT libtool)
- 编译日期: 2026-08-13
- 编译器: clang/clang++ (OHOS aarch64 原生构建)
- 状态: built

## 源码来源
- 上游仓库: https://code.videolan.org/jeeb/aribb24 （VideoLAN 维护的 aribb24 官方源，FFmpeg/VLC 引用同一仓库）
- 发布 tag: v1.0.4
- 源码包: `https://code.videolan.org/jeeb/aribb24/-/archive/v1.0.4/aribb24-v1.0.4.tar.bz2`
- sha256: `88b58dd760609372701087e25557ada9f7c6d973306c017067c5dcaf9e2c9710`
- 注: 原始 GitHub 仓库 (nkoriyama/aribb24) 最新 release 为 1.0.3，1.0.4 由 jeeb (Jan Ekström) 在 VideoLAN GitLab 维护，FFmpeg/FreeBSD/Cygwin 均以此为 1.0.4 官方源。

## 编译步骤
1. `get()` 下载源码包并 strip_root 解压
2. `apply_conandata_patches` 应用两个 configure.ac 补丁
3. `build_requirements()` 引入 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`（真机 HNP 只有 autoconf 套件，缺 automake/aclocal/libtoolize；tool_requires 用 build profile 解析）
4. build() 内显式 `autoreconf -fi` 自举（源码包无预生成 configure，仅含 configure.ac + bootstrap；`-i` 补装 install-sh/config.guess/config.sub/ltmain.sh 等辅助文件）
5. 对生成 configure 做 `umask 077 → 022` 修补（E114/E129，必须在 autoreconf 之后）
6. `configure --prefix=/ --enable-static --disable-shared` (+ OHOS 下 `--build/--host=aarch64-unknown-linux-gnu`)
7. `make -j1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `AC_PROG_CC_STDC` 在 autoconf >= 2.70 中被移除，autoreconf 直接失败 | 上游 configure.ac 使用旧宏 | 补丁 0001 删除该宏（AC_PROG_CC 已隐含 C99 检测） |
| 2 | `PKG_CHECK_MODULES(PNG, "libpng")` 依赖 pkg.m4，OHOS 构建环境不保证安装 pkg-config；且 libpng 仅为可选依赖（DRCS 位图导出） | 上游可选 libpng 检查 | 补丁 0002 移除该检查，`AC_SUBST([PKG_REQUIRES], [])` 保持 aribb24.pc 生成正常；不定义 HAVE_PNG，drcs.c 的 PNG 导出代码被 `#ifdef HAVE_PNG` 排除 |
| 3 | 原生 OHOS 构建时 configure 无法猜测 host 三元组 | AutotoolsToolchain 不注入 --build/--host，config.guess 不认识 HarmonyOS uname 输出 | OHOS 下显式传 `--build/--host=aarch64-unknown-linux-gnu`（autoreconf 重新生成的 config.sub 接受该标准三元组，与 a52dec 配方同法） |
| 4 | 源码包无 configure 脚本（git tree 快照，configure 是 autoreconf 产物不进版本库） | 上游只提交 configure.ac + bootstrap | 见问题 7（本轮修复） |
| 5 | 真机 preflight 报 `Failed to apply patch: 0002-configure.ac-drop-optional-libpng.patch`（`actual: b'pkg_requires=""'`） | conan 2.30 用 patch_ng（纯 Python）应用补丁，**严格按 hunk 头 `startsrc` 行号定位且不做偏移搜索**；0001 删除第 9 行 `AC_PROG_CC_STDC` 后文件整体上移 1 行，0002 的 `@@ -15,10 @@` 过期 → 在第 15 行（实际为 `pkg_requires=""`）找不到期望的 `# Checks for libraries.`。本机 GNU patch 能自动偏移所以本地难以复现 | 0002 hunk 头改为 `@@ -14,10 +14,4 @@`（对 0001 应用后的文件行号）；已用本地 patch_ng 1.19.1 按 0001→0002 顺序复现失败并验证修复成功 |
| 6 | preflight 日志首行 `preflight.sh[229]: can't create temporary file /tmp/shmmmtj6.tmp: Read-only file system`（HMBS 平台诊断 readonly_tmp） | 该行来自 HMBS 自身 preflight.sh 包装脚本（ksh 为 heredoc/进程替换创建临时文件）；非致命（conan create 继续执行，最终退出码 1 来自补丁失败） | 审计配方树：`grep /tmp|tempfile|mktemp` 零命中，配方/补丁/test_package 均未硬编码 /tmp；所有构建子进程（autoreconf/configure/make/grep）继承 HMBS 注入的 TMPDIR/TMP/TEMP，autoconf 生成的 configure 亦使用 $TMPDIR（ac_tmp）。无需代码改动 |
| 7 | 真机 preflight compile 失败：`/system/bin/sh: .../b/configure: inaccessible or not found` + `Error 127 while executing`（autotools.configure() 直接运行 `<source_folder>/configure`） | **conan 2.30 的 `Autotools.configure()` 不会自动运行 autoreconf**（对照 conan 2.30 源码 autotools.py：`configure()` 直接 `run("<source_folder>/configure")`，无自举逻辑）；且源码树缺 install-sh/config.guess/config.sub/ltmain.sh，裸 autoreconf 也会因缺辅助文件失败；真机 HNP 缺 automake/aclocal/libtoolize | ① `build_requirements()` 引入 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`（build profile 解析，同 musl-fts/argp-standalone 等 12+ 配方）；② build() 在 `apply_conandata_patches` 后、`autotools.configure()` 前，若 source_folder 无 configure 则 `autotools.autoreconf(args=["-fi"])`（-f 强制重生成、-i 补装辅助文件；autoreconf() 内部 chdir 到 source_folder）；③ autoreconf 之后把生成 configure 中 `umask 077` → `umask 022`（E114/E129：HMDFS 把 0700 临时目录变成不可写 drwx--S---，argp-standalone/advancescan/adolc 同法） |
| 8 | 真机 preflight compile 失败：`configure: error: working directory cannot be determined` + 大量 `getcwd: cannot access parent directories`（shell-init/job-working-directory 告警，errno 混杂 Not a tty/Bad address/ENOENT） | **HMDFS 下 conan 缓存父目录对 getcwd() 不可达**（nspr 4.37 注释：parent directories may be cleaned up during the build），叶子 build 目录存在且路径查找可用，但 getcwd() 沿父链上溯失败；autoconf 生成 configure 顶部严格 `pwd` 判定（2.70+ 为 `ac_pwd=\`pwd\` && test -n "$ac_pwd" && ... ls -di ...`，2.69 为 `if (pwd) >/dev/null 2>&1; then :; else`）直接 abort。adms 2.3.7 / nspr 4.37 已过门禁的同款问题 | 三重兜底（仿 nspr/adms 已验证组合）：① build() 开头 `os.chdir(self.build_folder)`（路径查找可用，仅 getcwd 不可用）+ try/except 兜底；② `os.environ["PWD"] = self.build_folder`（shell pwd 内建走逻辑路径 $PWD）；③ autoreconf 之后的 configure 改写循环里新增 pwd 判定回退：2.70+ 模式替换为 `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"` + 换行 `test -n "$ac_pwd" &&`（nspr 同款），2.69 模式替换为 `if (pwd) >/dev/null 2>&1 || test -n "$PWD"; then :; else`；`cd "$ac_pwd"` 与 `ls -di .` 均走路径查找不受影响。另因 cwd 已切到 build_folder，`_emit_upstream_test_result` 的审计 grep 改用 source_folder 绝对路径 |
| 9 | 真机 preflight compile 失败：`make install` 阶段 `install-dist_docDATA` 退出码 64（`.../bin/install -c -m 644 README.md COPYING '.../share/doc/aribb24'` → Error 64） | **E182/E188：真机 HMFS 上带 `-c` 的 install（toybox/HMBS shim）直接失败**，多源拷贝到目录形态必挂（adms 2.3.7 同款：二进制单源安装侥幸通过、多源安装退出 64）；平台能力 `chmod:0` + `install_shim:true`，无 GNU coreutils install。INSTALL_DATA='${INSTALL} -m 644' 展开后带 `-c` 后缀 | 仿 adms 2.3.7（已过门禁）在 conanfile 写 cp/mkdir install shim（容错 chmod，os.open 0o755 生成可执行文件），configure 后、make 前用 `_redirect_install_to_shim` 把生成 Makefile 的 `INSTALL =` 行改写为 shim 路径（INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动重算），make install 全程不碰真机 install |
| 10 | 真机 preflight test_package 失败：`Error in test() method, line 34: bin_path = os.path.join(self.cpp.build.bindirs[0], "test_aribb24")` → `IndexError: list index out of range` | **test_package 的 conanfile 未定义 `layout()`，Conan 2 不会自动填充 `self.cpp.build.bindirs`（空列表），`bindirs[0]` 越界**；构建与链接本身已成功（`[100%] Built target test_aribb24`），只卡在 test() 定位二进制 | 按仓库模板 `templates/test_package/conanfile.py.tmpl` 与已过门禁先例（aalib、aces_container）在 test_package 补 `def layout(self): cmake_layout(self)`——cmake_layout 将 build bindirs 置为 `["."]`（相对 build/<build_type>），test() 里 `os.path.join(".", "test_aribb24")` 即可命中 CMake 产物；import 增加 `cmake_layout` |
| 11 | 真机 preflight 判 incomplete（evidence 阶段）：「缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据」，上游测试 0/0/0/0/0；test_package 已过（HMBS_TEST_PACKAGE_RESULT 合法） | **标记产生阶段与 MANIFEST 声明不符**：MANIFEST 声明 `upstream_test_in_build: false`（按 hmbs 语义=上游证据由 test_package 阶段产生），但标记只在 conanfile.py build() 里用 `self.output.info()` 输出（带 conan 前缀 `aribb24/1.0.4: `，且不在 test_package 阶段），hmbs 按清单在 test_package 阶段抓不到该标记 → 判缺少证据（对照 wraplinux 轮 28 同款教训：`upstream_test_in_build: false` 必须走 test_package 阶段 echo/print 路径，osmctools/sipcalc/xidle 均如此过门禁） | ① 把 `HMBS_UPSTREAM_TEST_RESULT` no_tests 标记移到 `test_package/conanfile.py test()`，在真实运行 `./test_aribb24` 之后用裸 `print()` 输出合法 JSON（status=no_tests, discovered/executed=0, 含 reason）——对齐 xidle 先例（test_package print + upstream_test_in_build: false）；② conanfile.py build() 的 `_emit_upstream_test_result` 改为 `_audit_upstream_tests`，仅对真实源码树执行审计 grep 留机器证据，不再输出标记；③ 移除 conanfile.py 不再使用的 `import json` |

## 上游测试
- 审计结论: **上游无任何自动化测试**。
  - `Makefile.am` 仅声明 `lib_LTLIBRARIES`/`pkginclude_HEADERS`/`pkgconfig_DATA`/`dist_doc_DATA`，无 `TESTS`/`check_PROGRAMS`/`check-local` 目标；
  - `configure.ac` 无测试相关宏；
  - 发布包无 `tests/`/`test/` 目录。
- 处理: `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` + 非空 `upstream_test_audit`；`conanfile.py build()` 真实执行审计 grep 后输出 `HMBS_UPSTREAM_TEST_RESULT` no_tests 标记（discovered=0, executed=0, 含 reason）。

## test_package
- `test_aribb24.c`：实质调用 libaribb24 真实管线：
  1. `arib_instance_new` / `arib_get_parser` / `arib_get_decoder` 生命周期；
  2. `arib_parse_pes` 解析 caption 管理数据组（0x80）与语句数据组（0x81，携带 1 字节 caption data unit）；
  3. `arib_parser_get_data` 字节级校验解析结果；
  4. `arib_initialize_decoder_a_profile` + `arib_decode_buffer` 执行 JIS 解码。
  - 报文按 ARIB STD-B24 Volume 3 Chapter 5 独立 PES 传输协议逐位构造，已对照 parser.c 的 bs_read 边界检查确认不会越界。
  - assertion_count: 7。
- `test_package/conanfile.py test()` 运行二进制后输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=1, passedCount=1）。

## 依赖版本
- 无第三方编译依赖（libpng 可选检查已移除；系统库仅 libm）

## 验证结果
- 真机 preflight（2026-08-13 12:08）compile 失败：`configure: inaccessible or not found`（Error 127）→ 上轮修复：tool_requires automake/libtool + 显式 autoreconf -fi + 生成 configure 的 umask 077→022 修补。
- 真机 preflight（2026-08-13 13:42）compile 失败：`configure: error: working directory cannot be determined`（getcwd 父链不可达）→ 本轮修复：build() 开头 chdir(build_folder) + 预置 PWD + configure 的 pwd 判定失败回退 $PWD（2.70+/2.69 两种 autoconf 模式都处理）；审计 grep 改绝对路径。修改保持未提交工作树状态，等待 HMBS 真机预检复跑。
- 真机 preflight（2026-08-13 16:24）incomplete（evidence 阶段）：「缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据」→ 本轮修复（见问题表 #11）：标记移到 test_package 阶段裸 print 输出，build() 只留审计 grep。修改保持未提交工作树状态，等待 HMBS 真机预检复跑。
- 本机验证：`python -m py_compile` 通过；patch_ng 1.19.1 按 0001→0002 顺序应用补丁成功，补丁后 configure.ac 为干净 autoreconf 输入。
- 源码 sha256 由本机实测下载计算，与发布包一致。

## 注意事项
- aribb24 是 ARIB STD-B24 字幕解码库（FFmpeg libaribb24 封装、VLC 使用），LGPL-3.0-or-later。
- 安装产物: `include/aribb24/{aribb24,decoder,parser,bits}.h` + `lib/libaribb24.a` + `lib/pkgconfig/aribb24.pc`。
