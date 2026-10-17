# unbound 1.22.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 (/data/service/hnp/bin/clang)
- 三元组: aarch64-unknown-linux-ohos（native 编译，禁 --build/--host/--target，R1/R15）
- 状态: built

## 编译步骤

```bash
# 1. init-build（官方源）
python3 scripts/ohc-run.py init-build unbound 1.22.0 \
  --url=https://www.nlnetlabs.nl/downloads/unbound/unbound-1.22.0.tar.gz

# 2. 依赖（ohpcd 制品仓，W0 已确认发布）
conan install --requires=openssl/3.5.6.1 --requires=libevent/2.1.12 \
  --requires=expat/2.8.2 -r=ohpcd -pr=ci/conan/profiles/ohos-aarch64

# 3. configure（依赖路径指向 conan 包；--disable-flto 避免 LTO 链接过慢）
./configure --prefix=$DEFAULT_PREFIX \
  --with-ssl=$OPENSSL --with-libevent=$LIBEVENT --with-libexpat=$EXPAT \
  --disable-flto

# 4. 构建 + 隔离安装 + 测试
make -j1
make -j1 install DESTDIR=$TEST_PREFIX
make -j1 check            # 428 个 rpl 回放 + unittest(1270038 checks) + testbound selftest(33 checks) 全过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 无 __OHOS__ 分支，uname -s=HarmonyOS 无法匹配 | `patch-autotools-ohos.pl` 打补丁（LIBC 检测 + `*:HarmonyOS:*:*` case → `aarch64-unknown-linux-ohos`），config.sub 加 `ohos-linux`（E007） |
| 2 | config.status `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS setgid + umask 077 → drwx--S--- owner 不可写 | configure/config.status 中 `umask 077` → `umask 022`（E129） |
| 3 | `linux/net_tstamp.h` 引入 `redefinition of 'struct sockaddr_storage'` | OHOS SDK linux/socket.h 与 sys/socket.h 均定义 sockaddr_storage | conanfile.py `generate()` 在 OHOS 上 `extra_defines.append("_UAPI_LINUX_SOCKET_H")`（E119/R8，不用补丁 `#ifdef __OHOS__`） |
| 4 | 测试写 /tmp 失败（/tmp 只读） | 鸿蒙 /tmp 只读（E002），testcode 硬编码 `/tmp/...` | testcode/fake_event.c、testcode/unitauth.c 改用 `getenv("TMPDIR")`（缺省 /tmp），需要 #include <stdlib.h> |
| 5 | `-flto` 链接 unittest 极慢（数分钟无产出） | 大二进制 + LTO 链接在 clang 上极慢 | configure 加 `--disable-flto` |
| 6 | 扩展集成测试 `make longtest` 无法运行 | do-tests.sh 硬性要求外部工具 `ldns-testns`（ldns 包），环境中不存在 | 记录为外部工具依赖限制；核心 `make check` 已 100% 通过 |
| 7 | test_package 运行期 `libevent-2.1.so.7`/`libssl.so.3` 找不到（LD_LIBRARY_PATH 只有 expat） | libevent/openssl 配方未声明 `shared` 选项 → Conan `compute_package_type()` 解析为 UNKNOWN/static → `require.run=False` → VirtualRunEnv 不注入它们的 lib 目录 | conanfile.py `requirements()` 对三个依赖显式 `run=True`，传播到下游 run env |
| 8 | CI L2 smoke 门禁 `--version`/`--help` 全部失败（5 个工具 exit 1） | unbound 工具只支持短选项 getopt（`-V`/`-h`），且 `-h`/usage() 按上游设计 exit(1) | 新增 0008-long-options.patch：5 个工具在 getopt 前预处理 `--version`(打印 Version+PACKAGE_VERSION, exit 0)/`--help`(usage) |
| 9 | `unbound-checkconf -h` 打印 usage 但 exit 1 → test_package 误判失败 | 上游 `usage()` 设计为 exit(1) | test_package 改为生成最小 unbound.conf，用 `unbound-checkconf -o logfile <conf>` 实质校验配置（exit 0） |

## 源码修改（补丁由 finish refresh-patch --auto 生成）

- **config.guess**: `__OHOS__` LIBC 检测 + `*:HarmonyOS:*:*` 系统识别 case（→ aarch64-unknown-linux-ohos）
- **config.sub**: `ohos-linux` 三元组支持
- **configure**: `umask 077` → `umask 022`（2 处，config.status 由 configure 重新生成，无需单独打；配方 build() 内 replace_in_file）
- **E119**: 无源码补丁；OHOS 构建由 AutotoolsToolchain.extra_defines 注入 `_UAPI_LINUX_SOCKET_H`（R8）
- **testcode/fake_event.c**: `/tmp/testbound_...` → `getenv("TMPDIR")`（E002），加 `#include <stdlib.h>`
- **testcode/unitauth.c**: `/tmp/unbound.unittest...` → `getenv("TMPDIR")`（E002），加 `#include <stdlib.h>`
- **daemon/unbound.c / smallapp/unbound-checkconf.c / unbound-control.c / unbound-host.c / unbound-anchor.c**: getopt 前预处理 `--version`/`--help` 长选项（GNU CLI 兼容，L2 smoke 门禁要求 `--version` exit 0）

## 依赖版本

- **openssl**: 3.5.6.1 (ohpcd, conan 包, 静态库 libssl.a/libcrypto.a)
- **libevent**: 2.1.12 (ohpcd, conan 包)
- **expat**: 2.8.2 (ohpcd, conan 包)
- 可选依赖 nghttp2/protobuf-c 制品仓无配方 → 默认关闭（unbound 可选项，configure 未强制）

## 验证结果

```bash
$ ./unbound -V
Version 1.22.0
Linked libs: libevent 2.1.12-stable (it uses epoll), OpenSSL 3.5.6 7 Apr 2026
Linked modules: dns64 respip validator iterator

$ make check
test OK    # unittest 1270038 checks ok + testbound 33 checks + 428 rpl 全过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，conan create 构建） |
| conandata.yml | 官方源 URL + sha256 + 补丁声明 |
| test_package/ | 消费者测试（ub_ctx_create/ub_resolve + unbound-checkconf） |
| patches/ | 适配补丁（refresh-patch --auto 生成） |
| reports/test-report.md | 上游测试报告（make check 100%） |

## 注意事项

1. 二进制：unbound/unbound-checkconf/unbound-control/unbound-host/unbound-anchor（sbin）+ libunbound.so.8/a → 软件级 commands.json 需声明（R38）
2. 版本号 1.22.0（首次适配，不加后缀，R37）
3. conanfile.py 中 settings.os 判断用 `in ("Linux", "OHOS")`（R32）
4. build() 不能依赖未定义 shell 环境变量（R33），编译器/标志从 self.conf 获取
---

**编译结束**: 2026-08-06 21:08
**最终状态**: built
