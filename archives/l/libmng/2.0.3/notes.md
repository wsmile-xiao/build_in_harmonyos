# libmng 2.0.3 适配笔记

## 编译环境
- 构建系统: autotools (automake 1.13 tarball, 本机 1.16 — 见 patch 0003)
- 编译日期: 2026-09-11
- 编译器: OHOS SDK clang (target aarch64-linux-ohos), OpenHarmony PC (HarmonyOS aarch64)
- 分支: feat/libmng-2.0.3
- 状态: in_progress

## 上游核实（sourceforge libmng-devel/2.0.3）

### 源码与许可
- 官方 homepage: https://www.libmng.com/
- 官方 tarball: https://sourceforge.net/projects/libmng/files/libmng-devel/2.0.3/libmng-2.0.3.tar.gz
- SHA256: `cf112a1fb02f5b1c0fce5cab11ea8243852c139e669c44014125874b14b7dfaa`
  （本地 `sha256sum` 复核一致；解包后顶层目录 `libmng-2.0.3/`）
- License: Zlib（LICENSE 文件, libmng license 与 zlib 同源条款）
- 构建系统: autotools（configure/Makefile.am, 无 CMakeLists.txt 上游主路径）
- 库名/SONAME（上游/非 OHOS shared 能力）: libmng.so.2.0.2, SONAME
  libmng.so.2（libtool `-version-number 2:0:3`）; 静态 libmng.a。
  OHOS 交付为 static-only（见「静态/共享」）
- pkg-config: libmng.pc

### 依赖（configure.ac AC_CHECK_LIB 探测）
| 依赖 | 性质 | 探测结果 | 传播性 |
|---|---|---|---|
| zlib | 硬依赖 | -lz (HAVE_LIBZ) | public（libmng_types.h #include <zlib.h>）|
| jpeg | 可选 | -ljpeg (HAVE_LIBJPEG, MNG_INCLUDE_IJG6B) | public（#include <jpeglib.h>）|
| lcms2 | 可选 | -llcms2 (HAVE_LIBLCMS2, MNG_FULL_CMS) | public（#include <lcms2.h>）|

三者均启用（鸿蒙交付全功能），全部 transitive_headers=True 传播。

### 上游测试
- **无正式测试套件**: 无 test/ 目录; Makefile.am 未定义 check_PROGRAMS/TESTS;
  `make check` 仅递归 check-am → all-am（全量重链接, 无断言用例）
- tarball 自带官方 fixture: `contrib/gcc/gtk-mng-view/linux.mng`
  （101x127, 20 帧内嵌 PNG, TERM 无限循环动画）— 用于消费者测试
- CMake 构建路径（上游无）不适用; 此事实已记录于 manifest tests.upstream

## 关键适配点

### 1. AutotoolsDeps 假依赖（本配方最重要发现）
conan 2 AutotoolsDeps 生成器把 libjpeg-turbo 的两个组件（libjpeg +
turbojpeg）全部展开进 `LIBS="-llcms2 -ljpeg -lturbojpeg -lz"`。上游
configure.ac 用 AC_CHECK_LIB 逐项探测 jpeg/lcms2, 探测成功后 LIBS 原样
进入 Makefile → 链接期 libmng.so.2 出现多余 NEEDED `libturbojpeg.so.0`
（假依赖, libmng 源码 0 处引用 turbojpeg API）。

**解法**（elfutils 先例）: 不用 AutotoolsDeps; generate() 手工拼
CPPFLAGS(-I)/LDFLAGS(-L) + `unset LIBS`, 让 configure 自行探测出干净的
`LIBS=-lz -ljpeg -llcms2`。LD_LIBRARY_PATH 指向依赖包 lib/ 供 configure
运行期探测（本机即目标机, AC_CHECK_LIB 的 conftest 要能加载依赖 .so）。

### 2. E114 umask-mktemp（patch 0002）
HMDFS 上 `(umask 077 && mktemp -d "./confXXXXXX")` 可能返回成功，
但生成的目录随后无法写入，使 `config.status` 创建 `subs1.awk` 失败。
补丁绕过该假成功路径，改用上游已有的 `conf$$-$RANDOM` fallback 命名，
仍以 `(umask 077 && mkdir "$tmp")` 创建，并立即执行写入/删除探针；
目录不可写时 fail-closed，不通过放宽 umask 绕过权限问题。

### 3. automake 版本漂移（patch 0003, aaphoto 先例）
tarball 由 automake 1.13 生成, 本机 1.16。patch 0001/0002 触碰
configure mtime 后, make 触发 am--refresh 链（configure → aclocal.m4 →
automake 1.16 重跑）, 因 configure.ac 含 1.13 语法（且烙印
/sources/LIB/MNG/libmng-2.0.3 srcdir）而失败。补丁把 Makefile.in 中 4 条
重建规则 no-op 化（am--refresh/Makefile.in/configure/aclocal.m4/config.h.in）。

### 4. E074 make -j1
HMDFS 上 make jobserver mkfifo EPERM → `make -j1`。

### 5. 回调 ABI（消费者测试的坑, 全部踩过并修复）
- mng_readdisplay 强制要求回调: openstream/closestream/readdata/
  processheader/getcanvasline/refresh/gettickcount/settimer — 缺任一
  返回 MNG_NOCALLBACK(3)
- readdata 签名: `(mng_handle, mng_ptr, mng_uint32 buflen, mng_uint32 *read)`
- getcanvasline 返回 `mng_ptr`（行缓冲指针, 不能返回 NULL — display 直接写）
- 动画模式: settimer 返回 TRUE + 消费者循环 `mng_display_resume` 直到
  rc != MNG_NEEDTIMERWAIT(15); gettickcount 需虚拟时钟推进否则帧延时
  死循环（linux.mng TERM=无限循环, 真实时间永远走不完 — 用
  settimer 记录 delay, resume 前累加 tick）
- get_currentframe 在无 FRAM chunk 的流中恒 0（iFrameseq 只在 FRAM
  路径递增, linux.mng 用隐式 PNG 帧）— 帧进度断言改用 canvas 行数

### 6. 静态/共享
- 上游/非 OHOS shared 能力: shared=True 产出 libmng.so.2.0.2 + SONAME
  libmng.so.2 + libmng.so 符号链接
- OHOS 当前 static-only: 默认 shared=False, generate() 追加
  --enable-static --disable-shared → 交付 libmng.a（包内无 libmng.so*）
- OHOS + shared=True 在 validate() 显式拒绝（ConanInvalidConfiguration,
  bzip2 先例）, 不等到链接期报错, 也不用 linker 参数绕过重定位检查
- 根因: registry zlib/1.3.1 的 OHOS 包只有非 PIC 静态 libz.a, 链入
  shared libmng 触发 AArch64 绝对重定位错误（R_AARCH64_ADR_PREL_PG_HI21/
  R_AARCH64_ADD_ABS_LO12_NC, ld.lld 报 recompile with -fPIC）;
  非 OHOS 平台的 PIC zlib 不受影响
- fPIC: implements auto_shared_fpic

## 测试结果
- test_package: 31/31 通过（T1 官方 fixture/T2 程序化 MNG/T3 信息 API/
  T4 回调 ABI/T5 错误输入/T6 截断）
- test_ohos: 10/10 通过（H1 libmng.a 静态交付+归档成员 ELF64 LE
  AArch64/H2 消费者 NEEDED 闭包（jpeg/lcms2 shared, zlib 静态并入）+
  无 RPATH/H3 .codesign/H4 无宿主路径/H5 真实解码）
- 上游 make check: 通过但无断言（如上）

## W0 查重记录
- SONAME 知识: libharu(E316)/msdfgen draft 为 CMake set SOVERSION 路线;
  libmng 是 autotools -version-number 路线, 不重复
- 回调 ABI / 虚拟时钟动画模式 / AutotoolsDeps turbojpeg 假依赖: 无既有
  条目 → 建草稿（draft-E724 系列, 见 knowledge/drafts/）
