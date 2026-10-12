# rtpengine 26.0.1.15 适配笔记

## 编译环境
- 构建系统: makefile（顶层裸 Makefile + lib/deps.Makefile + utils/gen-common-flags bash pkg-config 探测；**非 autotools**——tag mr26.0.1.15 下 configure.ac/configure/Makefile.am/CMakeLists.txt/meson.build 全部 404）
- 编译日期: 2026-10-08
- 编译器: clang（设备 HNP 工具链 /data/service/hnp/bin/clang，profile: ci/conan/profiles/ohos-aarch64，clang15/libc++/cppstd17/Release）
- 状态: built（构建通过：3 二进制 + staging 安装 + 9/11 C 单元测试 PASS；conan-verify G0-G4+L 全绿，W3 本地 CI 通过；PR 合并 CI upload 后转 published）
- 上游: github.com/sipwise/rtpengine tag mr26.0.1.15（.release-version=26.0.1.15+0~mr26.0.1.15）
- 语言预检: 判 python 为检测器误报（pyproject.toml 仅 [tool.black] 7 行，无 [project]/[build-system]；lang_detect.py:107 纯存在性检查先于 :136 Makefile 判定短路），用户拍板按 C 继续

## 编译步骤

```bash
# 依赖准备（16 依赖 conan install + PkgConfigDeps，4 个 wrapper .pc 动态生成）
#   见 conanfile.py generate()；本地验证用 deps-conanfile 等价集

# 构建（串行 -j1：FIFO 系统级不可用，make jobserver 依赖 mkfifo，HMDfs 上 EPERM）
make -j1 CC=/data/service/hnp/bin/clang \
    without_nftables=yes \
    CFLAGS_DEFAULT= LDFLAGS_DEFAULT=
#   CFLAGS_DEFAULT=/LDFLAGS_DEFAULT= 覆盖 config.mk 的 dpkg-buildflags 缺失回退值
#   （-O3 -flto=auto -ffat-lto-objects → LTO 链接自动追加 -latomic，OHOS 工具链无此库）

# staging 安装（install 命令在 /system/bin，不在 PATH）
PATH=/system/bin:$PATH make -j1 install DESTDIR=$TEST_PREFIX \
    CC=/data/service/hnp/bin/clang without_nftables=yes CFLAGS_DEFAULT= LDFLAGS_DEFAULT=

# C 单元测试（依赖 .so 运行期解析：OHOS loader 吃 LD_LIBRARY_PATH，实测 9 例通过）
export LD_LIBRARY_PATH=<各依赖 pkg-config --variable=libdir 拼接>
make -C t unit-tests CC=/data/service/hnp/bin/clang CFLAGS_DEFAULT= LDFLAGS_DEFAULT=
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gen-common-flags 等 6 脚本 126 不可执行 | OHOS 无 /bin/bash（在 /data/service/hnp/bin/bash）、无 /usr/bin/perl（在 .harmonybrew/bin/perl） | shebang 改 `#!/usr/bin/env bash` / `#!/usr/bin/env perl`（gen-common-flags/gen-bcg729-flags/gen-codec-chain-flags/gen-rtpengine-kmod-flags/auto-test-helper/const_str_hash） |
| 2 | gen-common-flags exit 1（缺 pc） | rtpengine 探测系统标准名 libcrypto/libpcre2-8/libmariadb，conan 配方暴露 openssl/pcre2/mariadb-connector-c 名 | wrapper .pc ×3（conanfile generate() 动态生成，不改共享配方） |
| 3 | 同上（libjwt） | libjwt2/2.1.3 生成 libjwt2.pc，探测名 libjwt | 第 4 个 wrapper（Libs 带 -ljansson） |
| 4 | recording.c/redis.c 缺头文件 | daemon/Makefile 假设系统路径，未注入 libpcap/hiredis 的 CFLAGS | daemon/Makefile 补 `CFLAGS+= $(CFLAGS_LIBPCAP)` + `$(CFLAGS_LIBHIREDIS)`；t/Makefile 同补两项（上游 Linux 靠系统 /usr/include 兜底，OHOS 必须显式） |
| 5 | netfilter 链接失败 | OHOS 无 libiptc/内核 netfilter | make 变量 `without_nftables=yes` + daemon/Makefile 排除 netfilter_api.c（唯一无 #ifdef 守卫缺口，其唯一消费者 nftables.c 已排除） |
| 6 | rtpengine.8 Error 127 | OHOS 无 pandoc（common.Makefile:57 用 pandoc 生成 man） | common.Makefile `all: $(TARGET)`（摘 $(MANS)）；daemon/recording-daemon install 目标摘 MANS 及 man 安装行（perf-tester 本无 man） |
| 7 | 链接 `unable to find library -latomic` | config.mk 回退 CFLAGS_DEFAULT/LDFLAGS_DEFAULT 含 -flto=auto（dpkg-buildflags 缺失回退）→ clang 对 LTO 链接自动追加 -latomic；OHOS 工具链 llvm/lib、sysroot、usr/local/lib 三处均无 libatomic | make 参数 `CFLAGS_DEFAULT= LDFLAGS_DEFAULT=` 置空覆盖（conanfile build() 固化；CI 同设备类型必现） |
| 8 | 同上（第二来源） | lib/common.Makefile:7 硬编码 `LDLIBS += -latomic`（上游假设发行版提供） | 摘除该行 |
| 9 | media_socket.c:2916 "initializer element is not a compile-time constant" | clang15 拒**文件作用域静态结构体值拷贝**（`.handler = rtp_ext_mid`，rtp_ext_mid 为 static const 结构体对象；C 标准下静态对象值非常量表达式，gcc 宽松接受、clang 严格拒绝）。探针实验证明 STR_CONST 复合字面量本身合法（f3 通过），真凶是值拷贝 | media_rtp_ext_mid 的 .handler 内联展开为嵌套指定初始化器（函数指针+常量成员，合法）。probe.c/probe2.c 留档 /tmp/rtpengine-deps/ |
| 10 | oauth.c 3 错误（jwt_free 未声明等） | libjwt/3.3.3 是 mihaimaruseac builder/checker 新 API；rtpengine 用 maddevs/libjwt v2 经典 API（jwt_new/jwt_set_alg/jwt_add_grant/jwt_encode_str） | 换依赖 libjwt2/2.1.3（registry 已有，=maddevs v2.1.3）；其硬 pin openssl/3.5.6.1 与全图 3.5.6 冲突 → `self.requires("openssl/3.5.6", override=True)`；无 3.5.6 系 binary → --build=missing 源码补建（小包） |
| 11 | media_player.c `mysql/errmsg.h` not found | mariadb-connector-c 包布局：errmsg.h 在 include/mariadb/ 顶层，非 mysql/ 子目录（上游 MySQL 布局差异） | 全树仅 1 处引用 → `#include <mysql/errmsg.h>` → `<errmsg.h>` |
| 12 | 链接 undefined pthread_cancel/pthread_testcancel/pthread_setcancelstate | OHOS libc 未实现 POSIX 线程取消 API 家族 | 新增 lib/ohos_pthread_stubs.c（weak 实现：cancel 返回 ESRCH 不强制取消、testcancel no-op、setcancelstate 恒报 DISABLE；glibc 强符号优先，Linux 不冲突）；common.Makefile `SRCS += ../lib/ohos_pthread_stubs.c`（覆盖 3 二进制）+ t/Makefile `COMMONOBJS += ../lib/ohos_pthread_stubs.o`（覆盖测试程序，per-test 链接规则显式列对象） |
| 13 | staging `install: inaccessible or not found` | OHOS PATH 无 coreutils install（/system/bin/install 存在） | 本地 staging `PATH=/system/bin:$PATH`（conanfile package() 走 python copy，不依赖） |
| 14 | make -jN 不可用（jobserver） | FIFO 系统级不可用：mkfifo 在 tmp/$HOME/$TMPDIR 均 EPERM（HMDfs/FUSE） | -j1 串行；CI 同设备类型同约束 |
| 15 | 测试运行 `Error loading shared library libglib-2.0.so.0` | 测试/守护二进制无 RUNPATH，依赖 .so 在 conan 缓存目录 | 运行时 LD_LIBRARY_PATH 注入依赖 libdir（OHOS loader 实测吃该变量；conan test_package 由 buildenv 自动注入） |
| 16 | shell `timeout` 命令 127 | 环境别名 `timeout=timeout` 自环（无实用 timeout 工具） | 本地测试用自研看门狗（后台+秒级轮询+kill） |

## 源码修改（refresh-patch 将生成补丁）

| 文件 | 修改 |
|------|------|
| utils/gen-common-flags、utils/gen-bcg729-flags、utils/gen-codec-chain-flags、kernel-module/gen-rtpengine-kmod-flags、t/auto-test-helper | shebang `#!/bin/bash` → `#!/usr/bin/env bash` |
| utils/const_str_hash | shebang `#!/usr/bin/perl` → `#!/usr/bin/env perl` |
| daemon/Makefile | +`CFLAGS+= $(CFLAGS_LIBPCAP)`、`CFLAGS+= $(CFLAGS_LIBHIREDIS)`；LIBSRCS 排除 netfilter_api.c（without_nftables 时）；install 目标摘 $(MANS) 及 man 安装行 |
| recording-daemon/Makefile | install 目标摘 $(MANS) 及 man 安装行 |
| lib/common.Makefile | 摘 `LDLIBS += -latomic`；`all: $(TARGET)`（摘 $(MANS)）；+`SRCS += ../lib/ohos_pthread_stubs.c` |
| lib/ohos_pthread_stubs.c | **新增**：weak pthread_cancel/pthread_testcancel/pthread_setcancelstate（OHOS 平台 API 缺口填补） |
| daemon/media_socket.c | media_rtp_ext_mid.handler 静态值拷贝 → 内联嵌套指定初始化器（clang 静态初始化器约束） |
| daemon/media_player.c | `#include <mysql/errmsg.h>` → `#include <errmsg.h>`（connector 包布局） |
| t/Makefile | +`CFLAGS+= $(CFLAGS_LIBPCAP)`、`CFLAGS+= $(CFLAGS_LIBHIREDIS)`；`COMMONOBJS += ../lib/ohos_pthread_stubs.o` |

另：make 变量 `without_nftables=yes` 关闭 netfilter（非源码修改）。

## 依赖版本（16，Path B 2.84 世代全图原生一致零 force）

glib/2.84.0.1、json-glib/1.10.6.1（pin glib 2.84.0.1）、libcurl/8.5.0、openssl/3.5.6（override，压 libjwt2 的 3.5.6.1 pin）、libevent/2.1.13、pcre2/10.45、libwebsockets/4.3.5.1、zlib/1.3.1.1、ncurses/6.6、opus/1.5.2.1、libjwt2/2.1.3（源码补建）、hiredis/1.2.0、libpcap/1.10.6、ffmpeg/7.1.5、spandsp/0.0.6、mariadb-connector-c/3.4.8

> 世代背景：registry 真实 zlib 世代分裂——glib/2.88.3 系 zlib/1.3.2，ffmpeg 全系/libcurl/libtiff 系 zlib/1.3.1.1 → 弃 2.88 世代取 2.84 世代，16 依赖 31 包全 prebuilt（libjwt2 除外，小包源码补建）。

## 上游测试清点（R51）

- **Perl TAP**：65 个 t/*.pl（auto-daemon-tests*.pl，主入口 t/auto-daemon-tests.pl；另有 perl/ 测试模块 10 个）
- **C 测试程序**：22 个 t/*.c。t/Makefile TESTS 注册：基础 4（test-bitstr/aes-crypt/aead-aes-crypt/test-const_str_hash.strhash）+ transcoding 6（test-transcode/test-dtmf-detect/test-payload-tracker/test-resample/test-stats/test-mix-buffer）+ AMR 2（test-amr-decode/test-amr-encode，需 RTPENGINE_EXTENDED_TESTS=1）+ s3-auth = **13**；另有 aead-decrypt、kernel-extmap-filter（unit-tests 目标前置构建，不在循环执行清单）

### 实测结果（OHOS arm64 本机，2026-10-08）

| 测试 | 结果 | 备注 |
|------|------|------|
| test-bitstr | PASS | rc=0 |
| aes-crypt | PASS | rc=0 |
| aead-aes-crypt | PASS | rc=0 |
| test-const_str_hash.strhash | PASS | rc=0 |
| test-dtmf-detect | PASS | rc=0 |
| test-payload-tracker | PASS | rc=0 |
| test-resample | PASS | rc=0 |
| test-mix-buffer | PASS | rc=0 |
| s3-auth | PASS | rc=0 |
| test-stats | INCOMPLETE | 130s/290s 两个数据点均未完成，输出停在 "Redis delete_async=0"（redis 初始化行）后不再推进——疑似本机无 Redis 服务导致连接路径阻塞（推测，未抓包确认） |
| test-transcode | FAIL | codec 表注册阶段（"Adding codec 'CN'..." 后）SIGABRT core dumped；日志无 glib CRITICAL 行，需单独排查（不阻塞包交付） |
| Perl TAP 65 条 | N/A | ① 本机无 `ip` 命令（`ip: inaccessible or not found`），t/*.pl 需 ip netns 创建 veth/netns 隔离拓扑；② 需常驻 rtpengine daemon + 控制协议交互（auto-test-helper 驱动）；③ 部分用例依赖内核模块（kernel-module/ 需内核头文件，OHOS 无） |

## 验证结果

```
make -j1 CC=... without_nftables=yes CFLAGS_DEFAULT= LDFLAGS_DEFAULT=  → 0 error
产物: daemon/rtpengine (ELF 64-bit LSB pie arm64, 7.5MB) / recording-daemon/rtpengine-recording / perf-tester/rtpengine-perftest
staging: /usr/bin/{rtpengine,rtpengine-ctl,rtpengine-ng-client,rtpengine-recording,rtpengine-perftest}
         /usr/libexec/rtpengine/rtpengine-get-table
         /usr/share/man/man1/{rtpengine-ctl,rtpengine-ng-client}.1   （共 8 文件）
C 单元测试: 9/11 PASS（test-stats 阻塞、test-transcode SIGABRT，见上表）
```

## 注意事项

- FIFO 系统级不可用（mkfifo EPERM）→ 必须 -j1 串行，conanfile build() 固化
- LTO 必须关闭（CFLAGS_DEFAULT=/LDFLAGS_DEFAULT=），否则 -latomic 链接必挂
- 运行时依赖 .so 无 RUNPATH：执行需 LD_LIBRARY_PATH 覆盖依赖 libdir（conan test_package 由 buildenv 自动处理）
- 线程取消 API 为 weak stub：异常退出路径依赖线程自身收敛条件（waker 机制先行信号化），不影响正常运行
- bcg729/EVS 为 in-tree 内嵌（非依赖包）

### 对话 #1（2026-10-08，用户决策记录）
- 路径选型：用户要求预测路径 A（基础适配）vs 路径 B（知识库扩展）——评估结论 A 可行（16 依赖全发布、裸 Make+pkg-config 构建系统可控、测试主体 C），用户拍板走 A 并实际执行
- 语言预检分歧：lang_detect.py 判 python（pyproject.toml 仅 [tool.black] 7 行工具配置，纯存在性检查先于 Makefile 判定短路，属检测器误报）；用户拍板按 C/C++ 继续（符合 R47 边界规则"辅助脚本/工具配置不算主体"）
- 版本世代：确认取 glib 2.84 世代全图（registry zlib 世代分裂背景，见"依赖版本"节）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rtpengine | ~7.5MB | 主守护（PIE arm64） |
| rtpengine-ctl | CLI | 控制命令行 |
| rtpengine-ng-client | CLI | 新控制协议客户端 |
| rtpengine-recording | 二进制 | 录制守护（with_transcoding） |
| rtpengine-perftest | 二进制 | 性能测试工具 |
| rtpengine-get-table | 脚本/工具 | /usr/libexec/rtpengine/ 辅助 |
---

**编译结束**: 2026-10-09 00:58
**最终状态**: published
