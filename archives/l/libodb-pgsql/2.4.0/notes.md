# libodb-pgsql 2.4.0 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带已生成 configure，不跑 autoreconf——CI 设备无 automake）
- 编译日期: 2026-09-17
- 编译器: clang/clang++（/data/service/hnp/bin，profile ohos-aarch64，cppstd=17 libc++）
- 状态: built

## 编译步骤

单配方捆绑方案（Coordinator 裁定）：conan 包 `libodb-pgsql/2.4.0` 内先构建 libodb-2.4.0 核心
运行库，再以 `--with-libodb=<staging>` 构建 libodb-pgsql，最终打包两棵头文件树与
`odb`、`odb-pgsql` 两个库。仓内多组件先例: archives/p/postgresql/18.3。

1. `source()`: 分别下载 libodb-pgsql-2.4.0 与 libodb-2.4.0 两个官方 tarball（SHA256 固定于
   conandata.yml；codesynthesis.com 直连可达，且不在 CI 镜像 fallback 域名映射内）。
2. `build()`: apply_conandata_patches → 构建 libodb（out-of-tree, `-j1`, `make install
   DESTDIR=<build>/libodb-install`）→ 组装 `odb-staging/odb/`（odb/** 头文件 + libodb 库文件，
   供 m4/libodb.m4 的 `-I$DIR -L$DIR/odb -lodb` 布局）→ 以 `--with-libodb=<staging>` 构建
   libodb-pgsql。
3. libpq 来自已发布的 `postgresql/18.3`（requires()，R36 已满足）；configure 的 LIBPQ 宏做
   `libpq-fe.h + -lpq` 真实链接测试，generate() 把该包的 include/lib 追加进
   CPPFLAGS/LDFLAGS。
4. `package()`: pgsql `make install DESTDIR=<pkg>` + 拷贝 libodb 头文件/库，删除 `.la`，
   附带 GPLv2/LICENSE，OHOS 下对包内真实 ELF `.so*` 做 `llvm-objcopy --remove-section
   .codesign` + `binary-sign-tool sign -selfSign 1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++17 下 libodb 头文件编译失败：std::auto_ptr 特化/接口未加守卫（wrapper-traits.hxx、pointer-traits.hxx、database/connection 的 cache_query、lazy-ptr 全套、transfer-ptr 构造、lazy_unique_ptr/lazy_shared_ptr 的 auto_ptr 右值成员） | C++17 从 libc++/libstdc++ 移除了 std::auto_ptr；libodb 2.4.0 早于 C++17 | 在 odb/details/config.hxx 由 `__cplusplus >= 201703L` 派生 `ODB_NO_AUTO_PTR` 特性宏，用 `#ifndef ODB_NO_AUTO_PTR` 将上述接口编译出（语言标准判断，零平台宏，R8） |
| 2 | C++17 下 `throw (std::bad_alloc)` 报错（shared-ptr operator new 共 6 处） | ISO C++17 禁止动态异常规范 | 删除异常规范（所有标准下均合法） |
| 3 | C++17 下 `tree/version:1:1: expected unqualified-id` | tarball 源码根目录有纯文本文档文件 `version`；libc++ 的 `<memory>`/`<new>` 会 `#include <version>`，而 autotools 把 `-I$(top_srcdir)` 放进编译命令，文档文件遮蔽了 libc++ 真正的 `<version>` 头 | 从两个源码树的根目录与 dist_doc_DATA 中移除该文件（补丁 0001/0002）；conandata SHA256 在下载时校验，后处理不影响 |
| 4 | libodb 的 `--with-libodb=DIR` 布局特殊 | m4/libodb.m4 用 `-I$DIR -L$DIR/odb -lodb`：头文件与库文件必须同时在 `$DIR/odb` 下 | `_assemble_libodb_root()` 安装头文件到 `$DIR/odb/` 并拷入库文件、补 `libodb.so` 符号链接 |
| 5 | HMDFS 上 configure 报 `./confXXXXXX/subs1.awk: Permission denied` | autoconf 2.69 的 configure/config.status 用显式 `umask 077` 建 scratch 目录，HMDFS 拒绝在 0700 目录内建文件（E011 同类） | 补丁将两棵源码树 configure 与 config/config.guess 的 `umask 077` 改为 `022`（unixodbc/2.3.12 先例） |
| 6 | `make install DESTDIR=...` 产物落在 `usr/local/` 下 | 手工 configure 未传 `--prefix=/`，autoconf 默认 prefix=/usr/local | `_configure_args()` 显式追加 `--prefix=/`，DESTDIR 后即 `<dir>/lib`、`<dir>/include` |
| 7 | staging 组装后 `checking for libodb... no` | libtool `-release 2.4` 的产物名是 `libodb-2.4.so`（+ `libodb.so` 链接），staging glob 只匹配了 `libodb.so*` | staging 拷贝改为匹配全部 `libodb*` 条目并保留符号链接 |

## 源码修改

- `patches/0001-odb-cxx17-header-compat.patch`：libodb 2.4.0 的 0001 号 C++17 头文件兼容补丁
  （auto_ptr 编译出 + 动态异常规范移除 + `version` 遮蔽修复，14 个文件）。
- `patches/0002-libodb-pgsql-cxx17-header-compat.patch`：libodb-pgsql 2.4.0 树的 `version`
  遮蔽修复（Makefile.am/Makefile.in/删除 version 文件）。
- 设备端预验证：未打补丁 `-std=c++17` 复现失败（`version` 遮蔽）；打补丁后 C++17/14/11 三种
  模式下核心头文件 `-fsyntax-only` 全部通过（patch_ng 应用，与 conan 同引擎）。

## 依赖版本

- postgresql/18.3（libpq-fe.h、-lpq、pg_config；已发布到制品仓）

## 验证结果

```bash
bash ci/conan/build_and_test.sh libodb-pgsql/2.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 结论见交付报告；L0-L5 全链路 + test_package 真机执行
```

## 注意事项

- 上游无测试套件：`odb-tests-2.4.0` 需要 odb 代码生成编译器（宿主 GCC 插件，未移植）+ 真实
  PostgreSQL 服务器，CI 沙箱不可得；test_package 消费者测试给出可达成的最大证据。
- 制品仓 conandata 的 url 若日后回改镜像列表，L0j 归一化按文件名+sha256 对比，语义等价。
