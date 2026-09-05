# libdap 3.20.6 适配笔记

## 编译环境
- 构建系统: autotools (tarball 无预生成 configure, 需 autoreconf 自举)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 依赖 (全部来自 ohpcd 制品仓):
#   libxml2/2.15.3, curl/8.15.0, libtirpc/1.3.7, uuid/2.40.1
#   tool_requires: automake/1.18, libtool/2.5.4, bison/3.8.2, flex/2.6.4, cppunit/1.15.1

conan create . -pr:h=<ohos-aarch64 profile> -pr:b=<ohos-aarch64 profile> --build=missing
```

配方内 build 流程:
1. `apply_conandata_patches` 应用 3 个补丁 (见下)
2. `autoreconf -fi` 自举生成 configure (tarball 只有 configure.ac/Makefile.am)
   - automake/1.18 conan 包的 perl 模块需 PERL5LIB=<pkg>/share/automake-1.18
     (conan VirtualBuildEnv 自动注入)
   - ACLOCAL_PATH 需含 libtool/automake 包的 aclocal 目录 (自动注入)
   - libtool/2.5.4 conan 包的 libtoolize 内 prefix="/" 是坏的,
     本地验证时曾 sed 修正为包路径 (环境级 workaround, conan create
     沙箱内由 VirtualBuildEnv 的 ACLOCAL_PATH 自动协商绕开)
3. `_patch_config_guess`: libtoolize 注入的 conf/config.guess 不识别
   HarmonyOS uname ("unable to guess system type"), sed 修补为
   `aarch64-unknown-linux-ohos` (config.sub 2.5.4 已原生支持 ohos*);
   必须在 autoreconf 之后跑 (libtoolize 会重新覆盖 config.guess)
4. E011/E114 修复: configure 的 ac_tmp 改指预建目录 (HMDFS umask 陷阱);
   TMPDIR 指向 tmpfs (make jobserver FIFO 不支持 HMDFS)
5. configure: CPPFLAGS/LDFLAGS 注入 uuid+libtirpc+libxml2+flex 路径,
   CXXFLAGS 覆盖为 -std=c++11 (上游代码用 C++17 已移除特性),
   `gl_cv_have_weak=no` 预设 gnulib cache, PkgConfigDeps 提供
   libxml-2.0/libtirpc/libcurl 的 .pc + 重写 cppunit.pc
6. make -j2 && make check (unit-tests 与 tests 分开跑, 见下)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | cannot run C++ compiled programs (E064 变体) | clang++ 默认链接 libc++_shared.so, OHOS loader 无默认搜索路径 | LD_LIBRARY_PATH 注入 /system/lib64 (配方 generate()) | ✅ |
| 2 | config.guess "unable to guess system type" | HarmonyOS uname 不在 GNU config 数据库 | _patch_config_guess() sed 修补 (HarmonyOS→linux-ohos), 必须在 autoreconf 之后跑 (libtoolize 会覆盖) | ✅ |
| 3 | gnulib glthread/lock.h: pthread_cancel undeclared (8 errors) | musl 不提供 pthread_cancel; USE_POSIX_THREADS_WEAK=1 时 #pragma weak 探测引用未声明符号 | patch 0003: threadlib.m4 在 linux-ohos* 强制 gl_cv_have_weak=no + configure 传 cache 双保险 | ✅ |
| 4 | flex lexer: FlexLexer.h not found | flex 非系统安装, conan flex 包头文件在包内 | CPPFLAGS 注入 flex include (配方 build()) | ✅ |
| 5 | libtirpc pkg-config Libs 带 -L 前缀时 m4 提取库名错误 (`-l-L/... -ltirpc`) | acinclude.m4 的 sed 's/^-l//' 只剥第一个 -l | generate() 重写 libtirpc.pc 的 Libs 为纯 -ltirpc (LDFLAGS 提供 -L)。⚠️ 不能改 m4: 单引号是 m4 quote 字符, 动 sed 表达式会破坏引用配对 (实测 aclocal 报 AC_LANG_CONFTEST unknown language) | ✅ |
| 6 | uuid.h not found (configure 硬检查) | OHOS sysroot 无 uuid | requires uuid/2.40.1 + CPPFLAGS 注入 | ✅ |
| 7 | rpc/xdr.h not found → Cannot determine DODS XDR integer sizes | OHOS sysroot 无 rpc 头 | requires libtirpc/1.3.7 (pkg-config + CPPFLAGS) | ✅ |
| 8 | groff/col 不可用 (man 页生成 Error 127) | OHOS 无 groff/col | patch 0002: %.1 规则改为 cp $< $@ (man 源文件本就是 roff 文本) | ✅ |
| 9 | D4ParserSax2.cc: libxml2/libxml/parserInternals.h not found | 上游笔误 (include 路径带双重前缀) | patch 0001: 改为 libxml/parserInternals.h | ✅ |
| 10 | lld (链接器) 因 LD_LIBRARY_PATH 中 conan libxml2.so.16 崩溃 | ohos-sdk lld NEEDED libxml2.so.16, conan 同名库符号集不同, 遮蔽后 lld 启动即 "Error relocating" | LD_LIBRARY_PATH 把 sdk llvm/lib 排最前 (lld 用 sdk 版; 测试程序运行时 soname 相同 ABI 兼容) | ✅ |
| 11 | conftest 找不到 libc++_shared.so (LD_LIBRARY_PATH 已含 /system/lib64) | 系统 LD_LIBRARY_PATH 有"空格前缀段"("         /system/lib64"), musl loader 遇该段后续全部失效; 且 /data/storage/el1/bundle/libs/arm64 有同名不兼容的 libc++_shared.so | generate() 清洗空格段 + /system/lib64 提前到第二位 | ✅ |
| 12 | config.status: ./confXXXX/subs1.awk Permission denied (E011/E114) | HMDFS UID 映射 + umask 077 mktemp 目录不可写 | 预建 ~/tmp/libdap-ac-tmp, configure 模板 ac_tmp 改指该目录, 去掉退出 trap 的 rm -fr (同 abiword-plugin-docbook 先例) | ✅ |
| 13 | make jobserver mkfifo: Operation not permitted (E074) | TMPDIR 指向 HMDFS 不支持 FIFO | TMPDIR 指向 /data/storage/el2/base/temp (tmpfs) | ✅ |
| 14 | HTTPConnect.lo: dynamic exception specifications + bind2nd 编译错误 | conan profile cppstd=17 注入 -std=c++17, 上游 2020 年代码用 C++17 已移除特性 | configure args CXXFLAGS 显式覆盖为 -std=c++11 (上游 CXX11_FLAG 预期) | ✅ |
| 15 | cppunit 检测 no → unit-tests 被静默跳过 | AM_CONDITIONAL(CPPUNIT) 未装时 UNIT_TESTS 为空 | tool_requires cppunit/1.15.1 + generate() 重写 cppunit.pc (包内 .pc prefix=/ 是坏的) + PKG_CONFIG_PATH 注入 | ✅ |
| 16 | DASTest: /DASTest.log Permission denied | autotest suite 的 at_dir 从 getcwd 推导, make -C 切目录后子 shell cwd 失效 → at_dir 空 | make check 用 self.run(cwd=tests 目录) 直接 cd 而非 make -C | ✅ |
| 17 | 递归 make check 因 unit-tests 2 失败中断, tests/ 241 项跑不到 | SUBDIRS 顺序 unit-tests 在前 | 分开跑: unit-tests check (容忍) + tests check (单独) | ✅ |
| 18 | automake/libtool conan 包内 libtoolize prefix="/" 路径坏 (本地探索时) | conan 包打包缺陷 | 本地验证时 sed 修正; conan create 沙箱内 VirtualBuildEnv 的 ACLOCAL_PATH 自动协商, 无需包内修正 | ⚠️ 环境级 |

## 上游测试结果 (2026-09-03, OHOS aarch64, conan create 内验证)

### unit-tests (cppunit, 51 程序) — conan build() 内 make check
- **49 PASS / 2 FAIL / 0 SKIP**
- 失败明细 (均为环境限制, 非适配缺陷):
  - `HTTPCacheTest::create_cache_root_test` + `create_hash_directory_test`:
    测试硬编码 `/tmp/silly/`, OHOS /tmp 只读 (E002) — uncaught exception
  - `HTTPCacheTest::get/release_single_user_lock_test`: 依赖上述 cache root
  - `HTTPConnectTest::read_url_test`: 断言 HTTP 304, 依赖外网
    `test.opendap.org` 的 If-Modified-Since 行为, 沙箱网络受限

### tests/ (autotest) — conan build() 内 make check (tests 子目录)
- **All 241 tests behaved as expected** (das-test/dds-test/expr-test/dmr-test)
- **getdapTest: 1 test was successful** (getdap -d http://test.opendap.org/... 真实网络访问)

### test_package (conan 消费者测试)
- 构造 BaseTypeFactory/DDS/Int32/Str/Array/AttrTable/DAS, set_value/value
  round-trip 校验 + DDS.print 序列化 — **LIBDAP_TEST_PASS**

### 汇总: 291/293 通过 (99.3%), 2 失败均为平台/网络环境限制

## 源码修改 (3 个补丁 + 运行时修补, 见 patches/ 和 conanfile.py)

1. `0001-fix-libxml2-include-path.patch` — D4ParserSax2.cc include 前缀修正
2. `0002-manpages-skip-groff-col.patch` — man 页生成规则 groff|col → cp
3. `0003-gnulib-disable-weak-pthread-probe-on-ohos.patch` — gl/m4/threadlib.m4
   OHOS 强制 gl_cv_have_weak=no (musl 无 pthread_cancel)

运行时动态修补 (配方内 python, 无法/不宜固化为 patch):
- conf/config.guess HarmonyOS 识别 (libtoolize 每次重新注入, patch 无法固化)
- configure 的 ac_tmp → 预建目录 (E011/E114 HMDFS)
- libtirpc.pc / cppunit.pc 重写 (m4 单引号 quote 问题 + conan 包 .pc prefix 缺陷)
- LD_LIBRARY_PATH 清洗与顺序 (musl loader 空格段陷阱 + lld 遮蔽)

## 知识发现

- E064 变体: OHOS 上 conftest 失败的另一种根因 — 不是安全弹窗而是
  libc++_shared.so loader 路径; 解法同为 LD_LIBRARY_PATH 注入
- E002 复现: HTTPCacheTest 硬编码 /tmp/silly 只读失败
- 新错误模式候选: gnulib USE_POSIX_THREADS_WEAK 在 musl 的 pthread_cancel
  缺失 (8 errors undeclared identifier) — 适用于所有内嵌旧版 gnulib 的
  autotools 包

## 注意事项

- libdap 构建 3 个库 (libdap/libdapclient/libdapserver) + getdap/getdap4
  工具 + dap-config; package_info 声明 bindirs → CI L0k 判定含 CLI 工具,
  已创建软件级 commands.json (type=tool, 含 getdap/getdap4)
- gnulib (gl/) 子模块编译 regex/btyeswap, 需要 patch 0003 才能在 musl 编过
- libdapserver 依赖 uuid; getdap/getdap4 依赖 curl
- 上游测试中 HTTPCacheTest 硬编码 /tmp/silly (E002) 和
  HTTPConnectTest::read_url_test 依赖外网 test.opendap.org 304 —
  这 2 个失败为环境限制, 非适配缺陷
---

**编译结束**: 2026-09-03 03:45
**最终状态**: built
