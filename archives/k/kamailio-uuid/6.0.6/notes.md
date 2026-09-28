# kamailio-uuid 6.0.6 适配笔记

## 编译环境
- 构建系统: makefile（kamailio 经典 Makefile 体系，src/Makefile + Makefile.defs）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，/data/service/hnp/bin/clang）
- 状态: published

## 编译步骤

```bash
# 1) make cfg 生成 src/config.mak（探测 aarch64-unknown-linux-ohos 三元组）
make cfg include_modules=uuid LOCALBASE=<uuid pkg> BUILDER= \
    extra_defs='-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD \
    -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM \
    -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN'

# 2) 编译 uuid 模块（CPATH/LIBRARY_PATH 指向 uuid 包 include/lib）
make modules modules=modules/uuid -j1 LOCALBASE=<uuid pkg> BUILDER= \
    extra_defs='<同上>'
```

产物：`src/modules/uuid/uuid.so`（约 80KB，aarch64 ET_DYN，NEEDED 仅 libc.so，
libuuid 静态链入）。

## 历史先例核验（W0b）

同版本 kamailio 6.0.6 模块级适配已有三例先例（kamailio-snmpstats、
kamailio-unixodbc、kamailio-tls，分支 feat/kamailio-*-6.0.6），核心编译基础设施
（make cfg 探测 aarch64-unknown-linux-ohos、LOCALBASE 钉死手法、OS=harmonyos
平台宏缺失的 extra_defs 解法、CI 绿）已趟通。本次环境语义与先例一致（同一 SDK /
同一交叉编译器 / 同一 CI 能力矩阵：make + clang 均在 CI 可用），先例经验可迁移。

与 tls 先例的差异（本模块的独立判断）：
1) 依赖库不同：tls 探测 OpenSSL（变量 SSL_BUILDER/CRYPTO_BUILDER），uuid 探测
   libuuid（变量 BUILDER，见 src/modules/uuid/Makefile）。钉死手法同构但变量名不同，
   本次传 `BUILDER=`（make 命令行变量优先于 Makefile 内部赋值）。
2) 无随模块分发的 .cfg 示例文件：tls 包内额外打包 tls.cfg，uuid 模块源码目录
   只有 Makefile/README/CMakeLists.txt/doc/uuid_mod.c，故仅打包 uuid.so。
3) uuid 模块体量小（80256 字节，符号表未 strip），libuuid 为静态库布局。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OS=harmonyos 平台探测宏缺失（core 头 resolve.h/sched_yield.h 直接 #error） | Makefile.defs 只有 linux/solaris/freebsd/darwin 等分支；OS=harmonyos 不注入任何 HAVE_* 探测宏 | make 命令行 extra_defs 注入 linux 分支等价宏集（见编译步骤）。每个宏先对照 SDK sysroot 头文件实证：gethostbyname2 (netdb.h, _GNU_SOURCE 守卫内)、sched_yield/sched_setscheduler (sched.h)、MSG_NOSIGNAL/msg_control (sys/socket.h)、timegm (time.h)、ip_mreqn (netinet/in.h)、alloca.h 存在 |
| 2 | 模块 Makefile 的 libuuid 探测分支不确定（CROSS_COMPILE 为空时会用构建机 pkg-config 探测） | 优先级：BUILDER 命令行 > pkg-config（CROSS_COMPILE 空时）> LOCALBASE/SYSBASE 回退 | 显式传 `BUILDER=` 钉死 LOCALBASE 回退分支，LOCALBASE 指向 conan uuid 包目录（make 命令行变量优先于 Makefile 内部赋值），构建机系统 libuuid 无法劫持 |
| 3 | HAVE_UNION_SEMUN 取舍 | musl sys/sem.h 不导出 union semun 类型 | 不注入该宏：core lock_ops.h 在宏未定义时自带条件定义（实测编译通过），注入反而可能与 core 兜底定义冲突 |

## 源码修改

无。平台探测宏全部经 make 命令行 extra_defs 注入，未改任何源文件，0 补丁。

## 依赖版本

- uuid/2.40.1（conan 制品仓已发布；`conan download uuid/2.40.1 -r=ohpcd` 实测命中
  OHOS/armv8/clang15 预编译 binary，包内为 include/uuid/uuid.h + lib/libuuid.a 静态库布局）

## 上游测试清点（R51）

- kamailio 6.0.6 源码包顶层为 CMakeLists.txt / COPYING / ChangeLog / INSTALL /
  Makefile / README / cmake / doc / etc / misc / pkg / src / utils，不含 test/ 目录；
  utils/kamctl/dbtextdb/tests/ 是 kamctl 工具的 Python 测试数据，与 uuid 模块无关
- `src/modules/uuid/` 内仅 Makefile / README / CMakeLists.txt / doc/ / uuid_mod.c，
  find 无任何 *test*/*spec* 文件
- `src/modules/uuid/CMakeLists.txt` 无 add_test/enable_testing；顶层 Makefile 与
  src/Makefile 均无 check 目标
- 上游 CI（GitHub Actions）走 pkg/kamailio 的 Smoketest（需运行中的 SIP 场景），
  非源码内自动化套件

结论：上游无 uuid 模块自动化测试套件。适配侧测试为 test_package/check_uuid.py
产物结构校验（12 项断言，实测全 PASS：ELF 魔数 / ELFCLASS64 / ET_DYN / AArch64、
libuuid 静态链入符号标记 uuid_generate + uuid_unparse_lower + uuid_clear、模块入口
mod_register、licenses/COPYING 随包、NEEDED 无 libuuid、动态段无 RPATH/RUNPATH、
libuuid 真实 API 集合（15 个）无未解析符号）。

> 断言口径：uuid.so 由 kamailio 二进制运行时 loadmodule 加载，core 侧同 uuid 前缀
> 符号（如 sruid_uuid_api_set）应由宿主进程解析，故"未解析"判定仅针对 libuuid 真实
> API 集合，避免把宿主解析符号误报为依赖缺失。

## 验证结果

```bash
$ file src/modules/uuid/uuid.so
ELF shared object, 64-bit LSB arm64, not stripped
$ llvm-readelf -d uuid.so | grep NEEDED
  Shared library: [libc.so]        # libuuid 已静态链入
$ llvm-nm -D uuid.so | grep uuid_generate
00000000000050c4 T uuid_generate    # 定义符号（非 U）→ 静态链入实证
```

conan create 全量验证见 .ci-result.json（finish 自动写入）。
---

**编译结束**: 2026-09-25 21:57
**最终状态**: published
