# libodb 2.4.0 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带已生成 configure，不跑 autoreconf——CI 设备无 automake）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15（/data/service/hnp/bin，profile ohos-aarch64，cppstd=17 libc++）
- 状态: published

## 适配定位

libodb 2.4.0 本体的独立适配（上游从未单独发布；先例 archives/l/libodb-pgsql/2.4.0 是把核心库
捆绑在 pgsql 包内）。本配方零外部依赖（核心运行库只需 C++ 编译器 + POSIX 线程），独立打包
odb/** 头文件 + libodb-2.4.so。不 require 也不捎带 libodb-pgsql。

## 编译步骤（conan create 全自动）

1. `source()`: 官方源 https://www.codesynthesis.com/download/odb/2.4/libodb-2.4.0.tar.gz
   （SHA256 bfb9c398…a2d5c，与本地缓存 tarball 逐一比对一致）。
2. `build()`: apply_conandata_patches（0001 C++17/HMDFS 兼容补丁）→ `./configure --build/--host
   =aarch64-unknown-linux-gnu --prefix=/ --enable-shared` → `make -j1`。
3. `package()`: `make install DESTDIR=<pkg>`，删 `.la`，附 GPLv2/LICENSE，OHOS 下对包内 ELF
   `.so*` 做 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。

探索阶段（工作区 /storage/Users/currentUser/builds/libodb-2.4.0.work）已实测同一套
configure（需显式 `--build/--host=aarch64-unknown-linux-gnu`，鸿蒙内核 uname 使 config.guess
无法自判）+ `make -j1` 成功，产物 odb/.libs/libodb-2.4.so。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++17 下 libodb 头文件编译失败：std::auto_ptr 特化/接口未加守卫 | C++17 从 libc++/libstdc++ 移除了 std::auto_ptr；libodb 2.4.0 早于 C++17 | 在 odb/details/config.hxx 由 `__cplusplus >= 201703L` 派生 `ODB_NO_AUTO_PTR` 特性宏，用 `#ifndef ODB_NO_AUTO_PTR` 将相关接口编译出（语言标准判断，零平台宏，R8） |
| 2 | C++17 下 `throw (std::bad_alloc)` 报错（shared-ptr operator new） | ISO C++17 禁止动态异常规范 | 删除异常规范（所有标准下均合法） |
| 3 | C++17 下 `tree/version:1:1: expected unqualified-id` | tarball 源码根目录有纯文本文档文件 `version`；libc++ 的 `<memory>`/`<new>` 会 `#include <version>`，而 `-I$(top_srcdir)` 使文档文件遮蔽 libc++ 真正的 `<version>` 头 | 从源码根目录与 dist_doc_DATA 移除该文件（补丁 0001） |
| 4 | HMDFS 上 configure 报 `./confXXXXXX/... Permission denied` | autoconf 2.69 的 configure/config.guess 用显式 `umask 077` 建 scratch 目录，HMDFS 拒绝在 0700 目录内建文件（E011 同类） | 补丁将 umask 077 改为 022（unixodbc/2.3.12、libodb-pgsql 先例），并在配方 `_prepare_tmpdir()` 归一化 umask |
| 5 | configure: cannot guess build type | 鸿蒙内核 uname（HongMeng Kernel/HarmonyOS）不被 2015 年的 config.guess 识别 | 配置参数显式 `--build/--host=aarch64-unknown-linux-gnu`（与 libodb-pgsql/unixodbc 先例一致） |

## 源码修改

- `patches/0001-0018`（refresh-patch 按文件拆分的 18 个补丁，与 libodb-pgsql/2.4.0 的
  合并补丁 0001 同源，针对 libodb-2.4.0 树、路径去前缀后独立分发）：auto_ptr 编译出
  （0005-0018 头文件补丁，语言标准宏判断，无平台宏，R8/PF5 已过）+ 动态异常规范移除 +
  `version` 遮蔽修复（0001/0002 dist_doc_DATA，build() 内另做幂等删除）+
  autoconf/config.guess umask 077→022（0003/0004，HMDFS E011）。

## 依赖版本

- 无（libodb core 零依赖）

## 验证结果

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libodb 2.4.0
# G0-G4 + L2/L4/L5 全部 PASS（reports/conan-verify-report.md, verdict PASS）
# G2 conan create: 干净源码官方 URL 下载 → 补丁 → configure → make → package → test_package
# test_package 真机执行输出:
#   libodb 2.4.0 (odb 2.4) consumer test passed: refcount ok, exception NULL pointer|NULL pointer
```

上游测试清点（R51 三步法）详见 test_package/MANIFEST.yml：
tarball 无 tests/ 目录、Makefile.am 无 check 目标；真实测试套件 odb-tests-2.4.0 需要宿主 GCC
插件版 odb 编译器 + 数据库服务器，CI 沙箱不可得。探索阶段已实测 `make check`（rc=0，但为
automake 空 check-am 递归，无任何测试运行——已如实回填 0/0）。

## 注意事项

- 上游 `make check` 为 automake 空目标递归（odb/Makefile 无 check 规则），**不构成测试证据**；
  可达成的最大验证证据是 test_package 消费者测试（版本契约宏 + intrusive shared_ptr 引用计数
  + odb::exception 多态 what()/clone()，均为 libodb 导出符号）。
- 库类型包，无 commands.json（R38）。制品命名沿用上游 libtool `-release 2.4`（libodb-2.4.so）。
---

**编译结束**: 2026-09-27 14:50
**最终状态**: published
