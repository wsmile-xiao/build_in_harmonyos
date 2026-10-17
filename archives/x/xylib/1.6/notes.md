# xylib 1.6 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 自带预生成 configure）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（OHOS SDK）
- 平台: HarmonyOS PC (aarch64)
- 状态: built（真机预检前的工作树初稿）

## 上游信息
- 上游仓库: https://github.com/wojdyr/xylib
- 发布包: xylib-1.6.tar.bz2
- sha256: b641cb33fa01732b8203356e0978384f9551bf415cfbae5989b3a233b3cb0ec7
- 许可证: LGPL-2.1-or-later

## 构建方式
1. conan 下载并解压源码
2. apply_conandata_patches 应用 build-aux/config.guess、build-aux/config.sub 补丁
3. configure（--without-gui --enable-static --disable-shared）
4. make -j1
5. make install
6. package 阶段删除 libxy.la（libtool 便利归档）

## 依赖
- boost/1.90.0.4：仅头文件使用（boost/spirit、property_tree、cstdint、shared_ptr、algorithm/string、predef/endian）。1.90.0.x 后缀是本仓打包修订（非上游版本），mailio/pinocchio 已在 OHOS PC center 使用同修订。
- zlib/1.3.1.1：读 .gz 压缩源文件（AC_CHECK_LIB z gzopen）
- bzip2/1.0.8：读 .bz2 压缩源文件（AC_CHECK_LIB bz2 BZ2_bzReadOpen）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 aarch64-linux-ohos triplet | 上游 config.guess/sub 为 2018-02-24 版本，不认识 linux-ohos | 补丁 0001/0002：config.sub 的 maybe_os 列表与 OS 接受列表加 linux-ohos*；config.guess 加 LIBC=ohos 与 *:HarmonyOS:*:* 分支输出 aarch64-unknown-linux-ohos |
| 2 | GUI 依赖 wxWidgets，OHOS 未提供 | configure.ac 的 --with-gui 默认开启 | configure 传 --without-gui 关闭 xyconvert GUI |
| 3 | configure 脚本 /bin/sh 为 mksh 可能解析异常 | OHOS /system/bin/sh 是 mksh | 复用 xapian 模式：CONFIG_SHELL=/data/service/hnp/bin/bash + CC/CXX/AR/RANLIB 显式指定，经 bash 执行 configure |
| 4 | HMFS/HMDFS 下 getcwd/pwd 可能失败 | OHOS 存储不报告工作目录 | build() 中 os.chdir(build_folder)（try/except）+ os.environ["PWD"]=build_folder 预置 |
| 5 | config.status: ./confXXXXXX/subs1.awk: Permission denied | HMFS 按组判目录通行；Autoconf AS_TMPDIR 用 toybox `mktemp -d` 建出的临时目录（如 drwxr-s--x）同一进程随后也无法写入 subs1.awk，chmod 在 HMFS 为空操作；config.status 报 could not setup config files machinery | patches/0003-config-umask.patch：config.status 的 AS_TMPDIR 完全跳过 mktemp，直接用 Autoconf 的 plain `mkdir` fallback（`umask 022 && mkdir $tmp`），建出可写目录。上次仅把 umask 077→022 仍走 mktemp，目录仍旧不可写，故失败 |
| 6 | package 阶段 `make install`：libtool install 拷贝 libxy.a 失败，其后 `chmod 644 .../p//lib/libxy.a` 报 No such file or directory | 真机 HMFS 上带 `-c` 的 install（toybox/HMBS shim）直接失败（E182），libtool 的 install_prog 根本没把 libxy.a 拷进包目录；postinstall chmod 因文件不存在而失败。另 xyconv（libtool 包装程序）安装的 postinstall `chmod +x` 在 ELF 上返回 Permission denied（HMFS chmod 装饰性，能力为 0） | conanfile.py 引入 OHOS 安装 shim：写 cp/mkdir 版 `install` shim 并改写生成的 Makefile `INSTALL=<shim>`，使 libtool 的 install_prog/INSTALL_DATA 全程走 shim 拷贝；再写容错 `chmod` shim 并前置 PATH，ELF 上 chmod 失败不阻断 make install（对齐 adms 2.3.7 / libfstconst / aribb24 已过门禁先例） |
| 7 | 真机预检 compile 阶段报 `preflight.sh[306]: can't create temporary file /tmp/shikutdj.tmp: Read-only file system`（HMBS readonly_tmp 诊断，E002） | HMFS 上 /tmp 只读；bash（configure 进程替换/here-doc）、mktemp、llvm-ar/llvm-ranlib 与 make 的 shell 配方都向 `${TMPDIR:-/tmp}` 写临时文件，落到只读 /tmp 使编译/打包终止。上一轮只在 build() 里改 os.environ["TMPDIR"]——但 conan 的 autotools.configure()/make() 走 self.run(..., env="conanbuild")，环境来自 generate() 生成的 conanbuild 文件，build() 内 os.environ 未进入 conanbuild，故无效 | 在 generate() 用 self.buildenv.define("TMPDIR"/"TMP"/"TEMP") 定义可写临时目录（优先复用 hmbs 注入的 HMBS_TMPDIR/TMPDIR，否则 build 目录下自建 tmp），使 conanbuild 环境（autotools 的 configure/make 子进程均继承）拿到可写 TMPDIR；build() 内的 os.environ 设置保留作兜底（对齐 anubis 4.3 / asterisk-flite 已过门禁先例） |

## 源码修改
- patches/0001-config.guess.patch：识别 HarmonyOS（LIBC=ohos + HarmonyOS triplet）
- patches/0002-config.sub.patch：接受 linux-ohos target triplets
- 未修改功能源码，仅生成文件 config.guess/config.sub 的移植补丁

## 上游测试审计（no_tests）

**xylib 1.6 上游确无测试套件**，依据：
- 发布 tarball 无 tests/、test/ 目录
- Makefile.am 无 check/test 目标、无 TESTS/check_PROGRAMS 变量
- configure.ac 无测试宏，只做编译/头文件/库探测与可选依赖检测
- CMakeLists.txt 无 enable_testing()/add_test()

因此 test_package/MANIFEST.yml 声明 `upstream_tests_exist: false` +
非空 `upstream_test_audit`；test_package 的 C 程序输出真实 C API 断言计数，
conanfile test() 输出
`HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...,"discovered":0,"executed":0}`
并在 reason 中写明审计结论。

## test_package 消费者测试（真实 C API）
- test_xylib.c 链接 libxy 并校验：版本字符串、格式表注册数（≥10）、
  xylib_load_file() 解析 sample.txt 文本数据后的 block/列/行数与数据值
- 通过自建 sample.txt（2 列 3 行文本数据）做端到端解析，避免依赖在线样例

## 依赖版本（OHOS 工具链）
- conan: 2.x（OHOS 适配版）
- clang: 15
- make: GNU Make

## 问题 8：test_package 链接失败 `ld.lld: error: unable to find library -lbz2`
真机预检 compile 阶段，test_package 构建 test_xylib.c 时链接报
`unable to find library -lbz2`（ld.lld 停在该首个缺失库，实际 -lz 同理）。
根因：test_package/conanfile.py 的 build() 只用 `dep.cpp_info.libdirs`
（仅 xylib 自身 libdir）拼 -L，而 zlib/bzip2 的静态库位于各自 conan 包目录，
- L 未覆盖，链接器找不到 -lz/-lbz2。主库 libxy.a 之所以能链上是因为其链接
命令显式传了 zlib/bzip2 的 -L。修复：build() 遍历 `self.dependencies.values()`
收集整个依赖闭包的 libdirs 去重后拼 -L / rpath，使 -lz/-lbz2 可解析。

## 问题 9：test_package 断言 `text file parsed as 3 rows` 失败（7/8 passed）
真机 test_package 阶段 test_xylib 报 `[FAIL] text file parsed as 3 rows (line 85)`，
RESULT 7/8。根因：xylib 的 C API 列索引是 1-based —— `Block::get_column(0)`
返回伪"索引列"（index_column，`StepColumn(0,1)`，get_point_count()=-1 表示无限点），
真实数据列从 1 开始。原测试用 `xylib_count_rows(blk, 0)` 查的是索引列从而行数
异常（非 3），数据取值 `xylib_get_data(blk,0,0)`/`(blk,1,2)` 也会因 0 号列是索引
列而错位。修复：行数改查 `xylib_count_rows(blk, 1)`；数据断言改为 1-based 列
`xylib_get_data(blk,1,0)==1.0`（第一列第 0 行）、`xylib_get_data(blk,2,2)==6.0`
（第二列第 2 行）。
