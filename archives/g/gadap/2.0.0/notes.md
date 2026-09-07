# gadap 2.0.0 适配笔记（上游 gadap 2.0 同源码，2026-09-03 重写版）

## 编译环境
- 构建系统: autotools (tarball 自带 configure 2.59, 无需 autoreconf)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos, musl, libc++)
- 状态: built
- 分支: feat/gadap-2.0.0 (积分赛, 从 upstream/main 切出; 平台任务
  taskBranch=feat/gadap-2 与 conan 版本号规则冲突——conan 版本至少
  2 字符, 单段 "2" 无法 export, 已问卷反馈平台修正)
- 本次重写: 旧方案 (cmd-pkgs 系统包 + 机器路径) 已废弃, 改为 conan requires
  声明全部依赖 (libdap/3.20.6 本地 cache + 制品仓包)

## 编译步骤

```bash
conan create archives/g/gadap/2.0.0 --name=gadap --version=2.0.0 \
    -pr:h=~/.conan2/profiles/ohos-aarch64 \
    -pr:b=~/.conan2/profiles/ohos-aarch64
```

配方内 build 流程:
1. apply_conandata_patches 应用 11 个补丁 (0001 configure 修复;
   0002-0005/0008-0011 libdap 命名空间适配; 0006/0007 测试构建适配)
2. touch -r configure.ac 拉平 aclocal.m4/configure/Makefile.in 等时间戳
   (防 am--refresh 用设备 autoconf 2.72 重生成 configure 导致行号漂移
   + E011 config.status mktemp 陷阱复发)
3. configure: CC/CXX 从 tools.build:compiler_executables 注入 (R33),
   CXXFLAGS 显式覆盖 -std=c++11 (上游 2008 代码 strstream + libdap 头,
   profile cppstd=17 会编不过), DAP_CONFIG 指向 generate() 生成
   的重定位 dap-config
4. generate() 生成重定位 dap-config: libdap conan 包内 dap-config 的
   prefix=/ 为空且硬编码构建时 cache 路径 (打包缺陷), AC_CHECK_LIBDAP
   消费侧必须重写 — 输出 -I/-L 指向本机 conan 包目录 (libdap 配方
   重写 .pc 的同源手法)
5. make -j2 → libgadap.a + test 程序
6. make check + 上游 test 二进制冒烟 (无参数 → "need URL" rc=0)

## 依赖 (conan requires, W0 实测)

| 依赖 | 来源 | 验证方式 |
|------|------|----------|
| libdap/3.20.6 | 本地 conan cache | conan list + create 日志 "- Cache" |
| libxml2/2.15.3 | ohpcd 制品仓 | conan download --only-recipe |
| curl/8.15.0 | ohpcd 制品仓 | conan download --only-recipe |
| libtirpc/1.3.7 | ohpcd 制品仓 | conan download --only-recipe |
| uuid/2.40.1 | ohpcd 制品仓 | conan download --only-recipe |

libdap 显式 requires uuid/2.40.1 的原因: dap-config --libs 输出 -luuid
(libdapserver 链接需要), gadap 链接静态库时必须可见。
libxml2/curl/libtirpc 显式声明原因: libdap.a 静态链接的符号集合需要
这些库, 且 test_package 消费侧传递依赖可见性不可靠。

## 遇到的问题与解决方案 (本次重写)

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | make 触发 configure 用 autoconf 2.72 重生成, 0001 patch 行号漂移 + config.status mktemp umask 077 崩 (E011) | tar 保留 2008 时间戳, patch 后 configure 变新 → Makefile am--refresh/config.status --recheck 规则触发 AUTOCONF | build() 里 touch -r configure.ac 拉平 aclocal.m4/configure/Makefile.in/config.h.in/src/Makefile.in/test/Makefile.in/gadap-config.in 时间戳 | ✅ |
| 2 | dap-config 找不到 / 输出路径无效 | libdap conan 包 dap-config prefix=/ 空 + 硬编码构建时 cache 路径 (打包缺陷) | generate() 生成重定位版 dap-config (指向消费者 conan 包目录), DAP_CONFIG 环境变量注入 (AC_PATH_PROG 优先认绝对路径) | ✅ |
| 3 | rpc/types.h not found | libdap 头 xdr-datatypes.h include <rpc/types.h>, OHOS sysroot 无 rpc | 重定位 dap-config 的 --cflags 输出 -I<libtirpc>/include/tirpc | ✅ |
| 4 | test_package segfault: gadap_open(本地文件路径) 崩溃 | libdap 3.20.6 Connect 对非 http 名字走 _local 分支 (d_http=0), request_dds 解引用空指针 — 上游设计只支持 OPeNDAP 远程数据源 | 消费者测试改用不可达 http URL (127.0.0.1:1): libdap 抛 Error → gadap catch 返回错误码, 完整异常跨库传播验证 | ✅ |
| 5 | 错误码断言失败 | gadap 上游约定错误码 = errval(GADAP_ERR_*) = -1 * 枚举值 | test 断言 st == -GADAP_ERR_DAP_ERROR | ✅ |
| 6 | CXXFLAGS -std=c++17 编译失败 (strstream) | 上游 2008 代码 ostrstream + libdap 头, C++17 起移除 | configure args 显式覆盖 CXXFLAGS=-stdlib=libc++ -std=c++11 (libdap 配方同因) | ✅ |
| 7 | LD_LIBRARY_PATH 空格段陷阱 + lld 遮蔽 | musl loader 空格前缀段使后续段失效; conan libxml2.so.16 遮蔽 sdk lld 的 | generate() 清洗空格段 + sdk llvm/lib 最前 + /system/lib64 第二 (libdap 配方同源手法) | ✅ |
| 8 | 上游 test 真实数据测试 404 | test.opendap.org 测试服务器数据集路径已变动 (2026-09 实测) | 环境限制记录在案; 构建期验证 test 可构建可运行 (冒烟), 真实数据测试不纳入 pass/fail 判定 | ⚠️ 环境限制 |

## 上游测试结果 (2026-09-03, conan create 内验证)

- make check: src/test 两子目录 "Nothing to be done for 'check'"
  (automake 1.9 时代 test 是 bin_PROGRAMS, 无 check-PROGRAMS 注册,
  make check 即构建验证)
- 上游 test 二进制 (build-release/test/test): 链接成功 + 运行冒烟
  (无参数 → "need URL" 返回 0) — **链接/加载/运行验证通过**
- 真实数据测试: 依赖 http://test.opendap.org (服务器可达但数据集
  路径 404, 上游服务器内容变动; libdap getdap 工具同样 404) —
  环境限制, 非适配缺陷
- test_package (conan 消费者测试): 7/7 断言 PASS
  (gadap_numopen=0 / gadap_open(不可达URL) 返回 -GADAP_ERR_DAP_ERROR
  / handle 保持 -1 / numopen 仍 0 / gadap_handle 越界错误 /
  gadap_sq_new 无效句柄 NULL / GADAP_TEST_PASS)

## 与旧归档 (2026-08-03) 的差异

- 依赖方案: cmd-pkgs 系统包 (libdap 3.21.1 装到 ~/usr/local, 不可复现)
  → conan requires (libdap/3.20.6 + libxml2/curl/libtirpc/uuid)
- conanfile.py: 删除 _ensure_system_deps/_ensure_openssl_links/机器路径
  全部脏代码; 新增 generate() 重定位 dap-config + LD_LIBRARY_PATH 清洗
  + TMPDIR tmpfs + build() 时间序控制
- patches: 11 个全部复用 (3.20.6 与 3.21.1 的 namespace libdap 结构一致,
  实测干净应用); patch_classification 更新为 3.20.6 语境
- test_package: 空壳 → R34 真实 API 调用 (7 断言)

## 注意事项

- libdap 未发布到制品仓远程 (PR #7814 审核中) — 本 PR 停在提交前,
  等上游 libdap 合入发布后统一提交 (PF4 依赖闸会拦)
- 消费者代码不可用本地文件路径调 gadap_open (libdap _local 分支
  d_http=0, request_dds 空指针解引用) — 上游设计如此
---

**编译结束**: 2026-09-05 21:17
**最终状态**: built
