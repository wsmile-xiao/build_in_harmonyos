# kamailio-tls 6.0.6 适配笔记

## 编译环境
- 构建系统: makefile（kamailio 经典 Makefile 体系，src/Makefile + Makefile.defs）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，/data/service/hnp/bin/clang）
- 状态: published

## 编译步骤

```bash
# 1) make cfg 生成 src/config.mak（探测 aarch64-unknown-linux-ohos 三元组）
make cfg include_modules=tls SSL_BUILDER= CRYPTO_BUILDER= LOCALBASE=<openssl pkg> \
    extra_defs='-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD \
    -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM \
    -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN'

# 2) 编译 tls 模块（CPATH/LIBRARY_PATH 指向 openssl 包 include/lib）
make modules modules=modules/tls -j1 SSL_BUILDER= CRYPTO_BUILDER= \
    LOCALBASE=<openssl pkg> extra_defs='<同上>'
```

产物：`src/modules/tls/tls.so`（约 6.4MB，aarch64 ET_DYN，NEEDED 仅 libc.so，
OpenSSL 静态链入）。探索阶段验证：`file` 确认 aarch64 + 共享对象。

## 历史先例核验（W0b）

同版本 kamailio 6.0.6 模块级适配已有两例先例（分支 feat/kamailio-unixodbc-6.0.6、
feat/kamailio-snmpstats-6.0.6），核心编译基础设施（make cfg 探测 aarch64-unknown-linux-ohos、
LOCALBASE 钉死手法、CI 绿）已趟通。本次环境语义与先例一致（同一 SDK/同一交叉编译器），
先例经验可迁移。tls 与 unixodbc 的差异：tls 模块包含 core 头（resolve.h/sched_yield.h），
踩到了先例未覆盖的 OS=harmonyos 平台宏缺失问题（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | resolve.h #error "neither gethostbyname2 or getipnodebyname present"；sched_yield.h 走 fake sched_yield(sleep(0)) 宏与 sched.h 声明冲突 | Makefile.defs 只有 linux/solaris/freebsd/darwin 等分支；OS=harmonyos 不注入任何 HAVE_* 探测宏 | make 命令行 extra_defs 注入 linux 分支等价宏集（见编译步骤）。每个宏先对照 SDK sysroot 头文件实证：gethostbyname2 (netdb.h:135, _GNU_SOURCE 守卫内)、sched_yield/sched_setscheduler (sched.h)、MSG_NOSIGNAL/msg_control (sys/socket.h)、timegm (time.h)、ip_mreqn (netinet/in.h)、alloca.h 存在 |
| 2 | conan cache path 返回 export 目录（…/e）而非二进制包目录（…/p），CPATH 指错导致 openssl 头找不到 | conan cache path 对 recipe ref 返回 export folder | 用 `conan cache path "openssl/3.5.7:<package_id>"` 取二进制包目录，或先 `conan install --profile=ci/conan/profiles/ohos-aarch64 --build=missing` 实体化后取 `~/.conan2/p/opens*/p` |
| 3 | tls 模块 OpenSSL 探测分支不确定 | 模块 Makefile 优先级：SSL_BUILDER 命令行 > pkg-config（CROSS_COMPILE 空）> LOCALBASE | 显式传 SSL_BUILDER= CRYPTO_BUILDER= 钉死 LOCALBASE 回退分支（make 命令行变量优先级高于 Makefile 内部赋值） |
| 4 | HAVE_UNION_SEMUN 取舍 | musl sys/sem.h 不导出 union semun 类型 | 不注入该宏：core lock_ops.h:160 在宏未定义时自带条件定义（实测编译通过），注入反而可能与 core 兜底定义冲突 |

## 源码修改

无。平台探测宏全部经 make 命令行 extra_defs 注入，未改任何源文件，0 补丁。

## 依赖版本

- openssl/3.5.7（conan 制品仓已发布，`conan download openssl/3.5.7 -r=ohpcd --only-recipe` 实测通过，
  二进制经 `conan install --profile=ci/conan/profiles/ohos-aarch64 --build=missing` 实体化）

## 上游测试清点（R51）

- 顶层无 test/ 目录；utils/kamctl/dbtextdb/tests/ 是 kamctl 工具的 Python 测试数据，与 tls 模块无关
- src/modules/tls/ 内仅源码 + doc/，无测试源文件
- src/modules/tls/CMakeLists.txt 无 add_test/enable_testing；顶层与 src/Makefile 均无 check 目标
- 上游 CI（GitHub Actions）走 pkg/kamailio 的 Smoketest（需运行中的 SIP 场景），非源码内自动化套件

结论：上游无 tls 模块自动化测试套件。适配侧测试为 test_package/check_tls.py 产物结构校验
（11 项断言：ELF aarch64/ET_DYN、OpenSSL 静态链入符号证据、NEEDED 无 libssl/libcrypto、
tls.cfg/COPYING 随包、无 RPATH/RUNPATH 泄漏）。

## 验证结果

```bash
$ file src/modules/tls/tls.so
ELF shared object, 64-bit LSB arm64, not stripped
$ llvm-readelf -d tls.so | grep NEEDED
Shared library: [libc.so]     # OpenSSL 已静态链入
```

conan create 全量验证见 .ci-result.json（finish 自动写入）。
---

**编译结束**: 2026-09-25 21:23
**最终状态**: published
