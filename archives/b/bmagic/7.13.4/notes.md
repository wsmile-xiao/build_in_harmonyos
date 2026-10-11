# bmagic 7.13.4 适配笔记

## 编译环境

- 构建系统: header-only（上游 Makefile 驱动测试；配方内以 clang++ 同参直编复刻上游 GNU_CC 编译命令）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，Conan conf `tools.build:compiler_executables` 提供，R33）
- Conan: 2.29.1；CMake: 4.1.2（test_package）；Ninja: 1.13.1（test_package 生成器）
- 设备: HarmonyOS PC aarch64（uname: `HarmonyOS / HongMeng Kernel 1.12.0 / aarch64`），8 核
- 状态: built（conan-verify/W3 通过、release upload 未确认）

## 编译步骤

1. `source()` 下载官方 GitHub tag 归档并核对 SHA-256（conandata.yml）。
2. `build()` 复刻上游 `platforms/aarch64-linux-gnu.mk` GNU_CC 分支参数编译三套上游测试：
   `-D_REENTRANT -D_GNU_SOURCE -D__HarmonyOS_HongMeng__ -std=c++17 -Wall -O2 -g0`，
   链接 `-rdynamic -lpthread -ldl -lrt`（上游 SYS_LIBS）。
3. 包内完整运行 `ptest`（tests/test_threads，设备实测全部 OK，包内留证 2–4 分钟量级）；
   `bmtest`/`bmtest64` 单次全量为天数级（见下），包内编译留证 + 设备侧按上游选择器
   分块执行，2026-10-03 23:52 全部块跑完（bmtest 13/13、bmtest64 9/9，逐块 exit 0）。
4. `package()` 平铺安装 src/ 47 个头文件（上游消费惯例 `#include "bm.h"`）与 LICENSE。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `config.guess` 无法探测平台：临时目录内 `> dummy.c` 报 Permission denied；且 `canon-system` 无 OHOS 三连名匹配（uname -r 为 "HongMeng Kernel 1.12.0"） | (a) 本设备 FUSE 上 `umask 077 && mktemp -d` 产出 `drwx--S---`（2070）目录，属主也拒绝写入（chmod 700 后 FUSE 规范化为 2770 即可写）；(b) 上游平台 mk 仅识别 `*-linux-gnu*` 等三连名 | 用上游支持的 make 变量直接指定平台：`OSNAME=aarch64-linux-gnu`（makefile.in `ifndef OSNAME` 钩子），不修改上游文件；探索期编译均按此绕过 config.guess/canon-system |
| 2 | 上游 aarch64.mk 生成 `-D__HarmonyOS_HongMeng Kernel 1_12_0` 损坏编译命令（uname -r 含空格被拆成多个参数） | `OS_VER = -D__$(shell uname -s)_$(shell uname -r \| sed ...)` 在 OHOS uname 输出上必然损坏 | make 变量顶层覆盖 `OS_VER=-D__HarmonyOS_HongMeng__`（该宏上游仅作平台标签，无代码引用） |
| 3 | 上游链接的 bmtest/bmtest64/ptest 启动即段错误（exit 139，0.04s） | aarch64.mk `COMMON_LDFLAGS` 含 GNU ld 专有 `-export-dynamic`；OHOS 默认链接器 lld 解析为 `-e xport-dynamic`，ELF entry=0x0（readelf 实测） | 以语义等价、clang/lld 正确处理的 `-rdynamic` 覆盖 `COMMON_LDFLAGS`，用上游 `relink` 目标重链；重链后 entry 正常、二进制可运行 |
| 4 | 设备无 g++/gcc（上游 GNU_CC 分支硬编码 `CXX=g++`、`CC=gcc`） | 上游平台 mk 未提供 clang 分支 | make 变量 `CXX/CC/LD` 覆盖为 Conan conf 提供的 clang/clang++（R33） |

## 源码修改

无补丁。四项 OHOS 差异全部通过上游提供的 make 变量钩子（OSNAME/OS_VER/COMMON_LDFLAGS/CXX/CC/LD）
或配方内同参编译参数解决，上游源码零改动。

## 依赖版本

无外部依赖（W0）：src/ 公共头文件仅引用 C++ 标准库与自包含头（含内嵌 sse2neon.h），
无第三方库、无子模块。测试二进制仅需 -lpthread -ldl -lrt（OHOS 均可链接，实测）。

## 验证结果

```bash
# 上游测试构建（原生，OSNAME/OS_VER/COMMON_LDFLAGS/CXX/CC/LD 覆盖，不改上游文件）
. ./bmenv.sh
make -C tests/stress all OSNAME=aarch64-linux-gnu CXX=clang++ CC=clang LD=clang++ \
     OS_VER=-D__HarmonyOS_HongMeng__ COMMON_LDFLAGS=-rdynamic        # bmtest
make -C tests/stress64 all ...   # bmtest64
make -C tests/test_threads all ... # ptest

# ptest：完整运行，全部 OK
./ptest        # TOTAL; 6.546 min（2026-09-26 完整重跑），exit 0

# bmtest/bmtest64：单次全量为天数级（上游 tests/readme.txt: "runs for days"），
# 按上游自带选择器分块执行（每块独立旗标 + 独立工作目录 + done-*.txt 断点幂等），
# 2026-10-03 23:52 全部跑完，逐块 rc=0、零超时、零停牌：
#   bmtest   13/13 块、142 个测试调用点（实际执行旗标并集）
#   bmtest64  9/9  块、 79 个测试调用点
#   上游合计 229 = 142 + 79 + ptest 8 → PASS 229 / FAIL 0 / SKIP 0 / NOT_RUN 0
# 取数命令、三套候选口径与差额归因：test_package/MANIFEST.yml；逐块读数：reports/test-report.md
```

## 注意事项

- bmtest/bmtest64 单次全量为天数级，CI conan create 的 3600s 窗口仍无法容纳；
  CI/包内的运行证据以 ptest + 消费者 19 断言为准。设备侧分块全量执行已于
  2026-10-03 23:52 完成（bmtest 13/13 + bmtest64 9/9，上游 229 个单位 0 失败），
  逐块日志在 `$TASK_DIR/fullrun/logs/`（运行期日志不入库），逐块读数见
  reports/test-report.md。
- 上游 conandata 源为 GitHub tag 归档；bmagic.org 与 waterlan.home.xs4all.nl
  镜像均已失效（域名停放/主页下线），不要引用。
- test_package 使用 Ninja 生成器：HMMAC 拒绝 CMake "Unix Makefiles" try-compile
  的 /bin/sh exec（同仓 physunits-ct 先例）。
