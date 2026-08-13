# owamp 3.4-10 适配笔记

## 编译环境
- 构建系统: autotools（上游自带 configure 为 2014 版，config.sub 2009 版不识别 OHOS triplet，
  build() 中 `autoreconf -fi` 重新生成）
- 编译日期: 2026-08-13
- 编译器: clang/clang++ 15（OHOS SDK，conan profile: ci/conan/profiles/ohos-aarch64）
- 状态: built
- 目标平台: HarmonyOS PC (aarch64 / OHOS / armv8)

## 源码与方案
- 源码: Internet2 官方 `owamp-3.4-10.tar.gz`（自带 configure + aclocal.m4）
  - url: https://software.internet2.edu/sources/owamp/owamp-3.4-10.tar.gz
  - sha256: 059f0ab99b2b3d4addde91a68e6e3641c85ce3ae43b85fe9435841d950ee2fb3
- 依赖: **i2util/1.2**（configure.ac 硬性要求：`AC_SEARCH_LIBS([I2AddrByNode],I2util,...)` +
  `AC_CHECK_HEADERS([I2util/util.h I2util/conf.h],...)`，缺失即 configure 报错）——
  已发布到 ohpcd，W0/R35 全新缓存 `conan download` exit=0 核验通过
- 构建目录: owamp(库) owampd owping powstream conf test doc（test 产出上游测试程序 owtvec）

## 编译步骤
1. `conan download` 核验依赖可消费性（W0/R35）：i2util/1.2、automake/1.18、libtool/2.5.4 全部 exit=0
   （全新 CONAN_HOME，无本地缓存可绕过）；preflight_check.sh exit=0；R37 版本未占用
2. configure.ac 现代化补丁（automake 1.18 兼容 + VPATH 外源码构建修复，见补丁表）
3. conanfile.py:
   - `requirements`: i2util/1.2（真实硬依赖）
   - `build_requirements`: automake/1.18 + libtool/2.5.4（autoreconf 重新生成 config.sub）
   - `source()`: 下载 + apply_conandata_patches（5 个补丁）
   - `build()`: `autoreconf -fi` → `_drop_umask_077(configure)` → `autotools.configure()`
     （--build/--host=aarch64-unknown-linux-ohos + i2util 的 -I/-L）→ `make -j1` → 运行 owtvec
   - `package()`: `autotools.install()`
4. conan create 全绿: make 全部编译链接成功 + owtvec 自检 PASS（4 SEED × 6 EXP/SUM = 24 项）
   + test_package PASS（4 工具存在 + owtvec exit 0）
5. conan-verify 全绿: G0/G1/G2/G3/G4 + L2/L4/L5 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 手写补丁 hunk 行数不匹配（apply_conandata_patches 失败） | 手写 Makefile.am 补丁格式错误 | 用真实 `diff -u a/ b/` 生成补丁（本包全部 5 个补丁均真实 diff 生成） |
| 2 | export_sources 缺失导致补丁文件未导出 | conanfile.py 未实现 export_sources() | 增加 `export_sources()` 调 `export_conandata_patches(self)` |
| 3 | config.sub (2009) 不识别 aarch64-unknown-linux-ohos | 上游 tarball 自带 2014 configure + 2009 config.sub | build() 中 `autoreconf -fi` 用 tool_requires 的 automake/1.18 重新生成（同 clarisworks） |
| 4 | configure: Couldn't find I2util library | i2util include/lib 路径未注入（用了 AutotoolsToolchain 不存在的 cflags 属性） | 改用 `extra_cflags`/`extra_ldflags`，且 cpp_info 相对路径拼 `package_folder` 为绝对路径 |
| 5 | `owamp/config.h file not found`（api.o 编译失败） | VPATH 外源码构建：config.h 生成于 build 目录，OWPINCS 只有 `-I${top_srcdir}` | 补丁: OWPINCS 增加 `-I${top_builddir}` |
| 6 | `No rule to make target .../owamp/libowamp.a`（owampd 链接） | OWPLIBDEPS/OWP_dir 指向 `${top_srcdir}/owamp`（源码目录），VPATH 构建中库在 build 目录 | 补丁: OWP_dir 改为 `${top_builddir}/owamp` |
| 7 | `error: incompatible pointer to integer conversion assigning to 'off_t' from 'void *'`（api.c） | clang 15 严格模式：`phdr->oset_skiprecs = NULL`（off_t 为整数） | 补丁 0002: 改为 `(off_t)0` |
| 8 | `undefined symbol: ntp_adjtime`（owampd 链接） | OHOS musl libc 无 GNU 扩展 ntp_adjtime() | 补丁 0001+0003: configure.ac 增加 `AC_CHECK_FUNCS([... ntp_adjtime])`，time.c 两处 NTP 调用加 `#ifdef HAVE_NTP_ADJTIME` 守卫 |
| 9 | `no member named 'childwait'`（owping.c 编译） | owpingP.h 中 childwait 成员被 `#ifndef NDEBUG` 守卫，Release 构建定义 NDEBUG 后成员消失，但 owping.c 无条件引用 | 补丁 0004: 去掉 NDEBUG 守卫 |
| 10 | owtvec 运行 SIGSEGV（Signal 11） | 上游经典 assert 副作用 bug：`assert((exp = OWPExpContextCreate(...)))` 在 NDEBUG（Release）下赋值被编译掉，exp 未初始化 → 野指针 | 补丁 0005: 赋值移出 assert |
| 11 | finish W3 门禁 L1 "fake test detected" | test_package/conanfile.py test() 中 `owping -h ... || true` 触发 CI 假测试正则 | 移除 `|| true`，test() 只做真实存在性检查 + 运行 owtvec |
| 12 | config.status 创建临时目录失败（E114） | HMDFS umask 077 建 0700 临时目录不可写 | conanfile.py `_drop_umask_077()`（已有正式条目 E114） |
| 13 | make 并行 jobserver FIFO EPERM（E074） | 鸿蒙 SELinux 禁止 FIFO | 全部 make 调用 `-j1`（已有正式条目 E074） |

## 源码修改（补丁，全部真实 diff 生成）

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-configure.ac.patch | automake 1.18 兼容（AM_INIT_AUTOMAKE([foreign]) + AC_CONFIG_HEADERS + AC_CONFIG_MACRO_DIR([config])）；OWPINCS 加 -I${top_builddir}；OWP_dir 改 ${top_builddir}/owamp；AC_CHECK_FUNCS 加 ntp_adjtime |
| patches/0002-api.c.patch | `oset_skiprecs = NULL` → `(off_t)0`（clang 15 -Wint-conversion） |
| patches/0003-time.c.patch | 两处 `ntp_adjtime()` 调用加 `#ifdef HAVE_NTP_ADJTIME` 守卫（OHOS musl 无此 GNU 扩展） |
| patches/0004-owpingP.h.patch | 去掉 `opt.childwait` 的 `#ifndef NDEBUG` 守卫（owping.c 无条件引用） |
| patches/0005-owtvec.c.patch | assert 副作用修复：`exp = OWPExpContextCreate(...)` 移出 assert（NDEBUG 下不再被编译掉） |

## 依赖版本
- conan 依赖: i2util/1.2（真实硬链接依赖，configure 必需）
- 编译工具链: OHOS SDK clang/clang++ 15、tool_requires automake/1.18 + libtool/2.5.4
- 运行时: owampd/owping/powstream/owtvec 均为静态链接（libowamp.a + libI2util.a）

## 验证结果
```bash
# W0 依赖核验（R35，全新 CONAN_HOME，无本地缓存绕过）
conan download "i2util/1.2" -r=ohpcd --only-recipe   # exit=0
conan download "automake/1.18" -r=ohpcd --only-recipe # exit=0
conan download "libtool/2.5.4" -r=ohpcd --only-recipe # exit=0
bash ci/scripts/preflight_check.sh owamp/3.4-10 --deps "i2util/1.2"  # exit=0, [OK] 已发布

# conan create（clean source，全绿）
conan create archives/o/owamp/3.4-10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → make 全绿（owamp lib + owampd/owping/powstream/owtvec 编译链接成功）
# → owtvec 自检 PASS（4 SEED × 6 EXP/SUM 检查点，exit 0）
# → test_package PASS（4 工具存在 + owtvec exit 0）

# 上游测试单独执行（任务4）
./owtvec  # exit=0，24 项 EXP/SUM 输出，日志 owamp-archive/owtvec-run.log

# conan-verify
python3 scripts/ohc-run.py conan-verify owamp 3.4-10 --profile ohos-aarch64
# → G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS，可标记 published
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，-j1，umask 修复，autoreconf -fi，i2util 依赖注入） |
| conandata.yml | 源码 URL + sha256 + 5 个补丁声明 |
| patches/0001~0005 | 5 个平台/可移植性补丁（全部真实 diff 生成） |
| test_package/ | conan 消费测试（4 工具存在性 + owtvec 运行） |

## 注意事项
- **i2util/1.2 是 owamp 的真实硬依赖**（configure 强制），不是可选项——必须声明于 requirements()
- 补丁必须用真实 diff 生成（手写 hunk 行数不匹配会导致 apply_conandata_patches 失败）
- 补丁 diff 必须使用 a/ b/ 相对路径（绝对路径会被 patch 工具拒绝）
- 知识条目: E114（umask 077 / HMDFS）、E074（make -j1 FIFO）
- make 必须 -j1（E074）；configure 生成后必须去除 umask 077（E114）
- 系统 channel 已用 `@ohpcd/stable` 构建验证
---

**编译结束**: 2026-08-13 11:20
**最终状态**: built
