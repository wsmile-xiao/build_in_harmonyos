# libabigail 1.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-04
- 编译器: clang/clang++（OHOS SDK，aarch64-linux-ohos，libc++）
- 状态: built

## 编译步骤
1. `ohc-run.py init-build libabigail 1.4 --url=https://sourceware.org/pub/libabigail/libabigail-1.4.tar.gz`
   （sha256=27914ea1fda0af3fe8678101abea4733b9f7e7b6b5c576536b7bfa4e8189289f）
2. 用 `conan install` 安装预编译依赖 libxml2/2.15.3、elfutils/0.195、musl-fts/1.2.7（ohpcd 制品仓）
3. `./configure --prefix=<prefix>`，依赖头/库经 CPPFLAGS/LDFLAGS/LIBS 喂给 configure
   （AC_CHECK_LIB 探测 libelf/libdw，PKG_CHECK_MODULES 探测 libxml-2.0）
4. `make` → `make install DESTDIR=$TEST_PREFIX`
5. `make check`（14/17 通过，3 项平台/基线差异，见"验证结果"）
6. `conan-init` 生成 conanfile.py + conandata.yml + test_package/ → `conan-verify` → `finish`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 unrecognized system type（E007） | 2013/2015 版 config.guess/config.sub 不认识 HarmonyOS | 补丁 0001/0002：识别 `aarch64-unknown-linux-ohos`；2015 版 config.guess 每个 case 分支必须自带 echo+exit |
| 2 | configure/config.status 临时目录 Permission denied（E129） | HMDFS setgid + umask 077，新建目录对 owner 不可写 | 补丁 0003（configure umask 077→022）+ build() 内幂等重刷（configure 为生成文件，patch 可能被 autoreconf 再生成失效） |
| 3 | 找不到 `<tr1/...>` 头 | libc++ 无 TR1 头 | C++11 现代化：`std::tr1::*` → `std::*`（补丁 0004-0036 涉及各头文件/源码） |
| 4 | CI 源码下载 IncompleteRead / 单镜像过慢超时（~150MB） | worker 访问 sourceware/kernel.org 不稳定或仅 ~10KB/s，吃满 2700s | conandata 权威镜像 URL 列表（tuna→mirrorservice→kernel→sourceware，同 sha256）+ source() 慢速/中断失败切换与 DOWNLOAD_CACHE（同 linux-headers）；默认 make 并行 min(cpu,20) |
| 12 | CI configure：C++ compiler cannot create executables（#13333/#14253） | `cpp_info.libdirs` 相对路径 + `package_folder` 空时 `join('','lib')`→`-Llib`；AC_PROG_CXX 带着 LIBS=-lxml2… 链接失败 | host 依赖绝对化且校验目录存在；剥离继承环境相对 -I/-L；拒绝仍含 `-Llib` 的 LDFLAGS（对齐 gd join(package_folder)） |
| 13 | CI #14152：清掉 -Llib 后仍 AC_PROG_CXX 失败 | LIBS 预填整棵 `-lxml2 -lelf …`，空 conftest 被迫链依赖树 | LIBS 仅留 `-lfts`；-I/-L + LD_LIBRARY_PATH；PkgConfigDeps 供 libxml；AC_CHECK_LIB 自行加 -l* |
| 14 | CI #14268：lld xmlFreeDoc symbol not found | Conan libxml2 进 LD_LIBRARY_PATH 抢在 SDK 前，污染 lld 自身依赖（E120/E132） | LD_LIBRARY_PATH 置顶 SDK `llvm/lib`（同 openblas/morpheus） |
| 4 | `__gnu_cxx::stdio_filebuf` 不存在 | libc++ 无 libstdc++ 扩展头 | temp_file 改用 `std::fstream`（补丁 0024） |
| 5 | `/tmp` 只读（E002），temp_file 建临时文件失败 | OHOS /tmp 只读 | temp_file 优先使用 $TMPDIR（补丁 0024） |
| 6 | `__floatditf/__fixtfdi` 未定义符号 | AArch64 long double 是 quad-float，需 compiler-rt 提供软浮点转换 | 去掉 long double 参与的 abs() 重载（补丁 0019） |
| 7 | `fts.h` 不存在 | OHOS 无系统 fts | 依赖 musl-fts/1.2.7（提供 fts.h/libfts），-lfts 显式进 LIBS |
| 8 | `get_current_dir_name` 不存在 | GNU 扩展，musl 无 | 改用 `getcwd`（补丁 0024） |
| 9 | `basename` 隐式声明 | 缺 `libgen.h` | 补丁 0037：新增 `#include <libgen.h>` |
| 10 | C++11 `shared_ptr::operator bool` 为 explicit | TR1 允许隐式转换，C++11 不允许 | 显式 bool 转换（补丁 0019/0021/0022/0036） |
| 11 | conanfile/manifest 误标 Apache-2.0 | 模板默认 license | 改为上游实际许可证 `LGPL-3.0-or-later` |

## 源码修改

37 个补丁（archives/l/libabigail/1.4/patches/0001-0037）：
- 构建系统：0001 config.guess、0002 config.sub、0003 configure（umask）
- tr1→std 现代化：0004-0017、0020、0023、0025-0036（各 include/*.h、src/*.cc、tools/*.cc、tests/*.cc）
- 平台可移植性：0018（去 stdio_filebuf）、0019（abs 去 long double）、0021/0022/0036（shared_ptr→bool）、0024（temp_file→fstream+TMPDIR、getcwd）、0037（libgen.h）

## 依赖版本

- libxml2/2.15.3（XML 解析，PKG_CHECK_MODULES 探测 libxml-2.0）
- elfutils/0.195（libelf/libdw，AC_CHECK_LIB 探测）
- musl-fts/1.2.7（fts.h/libfts，configure 不探测，-lfts 显式进 LIBS）

## 验证结果

```bash
$ abidw --version
1.4.0
$ make check
14/17 通过；3 项失败均为平台/基线差异，非功能缺陷：
  - runtestdifffilter: demangler 输出格式差异（libc++ demangler vs 上游 g++ 基线）
  - runtestdiffpkg: 报告文本中 libdw 版本字符串与基线不同（elfutils/0.195 版本）
  - 若干测试脚本 /bin/bash shebang（OHOS 无 /bin/bash，相关 shell 驱动测试跳过）
$ conan create（test_package）：
  test_libabigail 构造 abigail::ir::environment + get_library_version_string → OK
  abidw --version → 1.4.0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools；默认并行 min(cpu,20)；_sign_binaries 与 elfutils/libxml2 同法；大源包镜像 failover） |
| conandata.yml | 权威镜像 URL 列表 + 真实 sha256 + 37 补丁声明 |
| test_package/ | test_libabigail.cc 实质调用库 API（R34）+ abidw --version |
| patches/0001-0037 | 全部适配补丁 |
| manifest.yaml | 编译元数据（status: built） |
| reports/test-report.md | make check 测试报告 |

## 注意事项

- 产物含可执行工具（abidw/abidiff/abilint 等），已按 R38 声明软件级 commands.json；.so 与可执行文件按鸿蒙 XPM 要求做代码签名（_sign_binaries，llvm-objcopy + binary-sign-tool）
- 依赖的共享库运行期可见性：构建期用 LD_LIBRARY_PATH，不用 -Wl,-rpath（避免把 conan cache 绝对路径烤进 RPATH）
- 版本号严格 1.4（首次适配上游版本，无后缀）
---

**编译结束**: 2026-08-04 21:32
**最终状态**: built
