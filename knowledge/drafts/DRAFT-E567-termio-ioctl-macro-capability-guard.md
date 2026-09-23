# DRAFT-E567 — termio ioctl 宏不存在时用编译期能力守卫隔离 legacy 分支

## 错误特征

在 musl/aarch64(OHOS、Alpine 等)平台编译带终端控制功能的 C 代码时,报:

```
src/run.c:76:11: error: use of undeclared identifier 'TCGETA'
src/run.c:76:11: error: use of undeclared identifier 'TCSETA'
error: 'struct termio' has no member named 'c_cc'
```

触发宏族:TCGETA、TCSETA、TCSETAW、TCSETAF(legacy System V termio API)以及
struct termio 类型本身。

## 触发条件

- 构建系统: 任意(cc/clang 直接编译,cmake/autotools/meson 均可)
- 阶段: compilation
- libc: musl(或任何不提供 legacy System V termio 宏的 libc)
- 代码模式: 直接使用 TC* 宏、或存在 termio/termios 双分支 + 回退 #define

## 根因分析

旧式 System V termio API(TCGETA/TCSETA/TCSETAW/TCSETAF + struct termio)**从未
被 POSIX 标准化**;POSIX 只标准化了 termios(tcgetattr/tcsetattr + struct
termios)。glibc 为兼容历史 System V 代码在 `<termio.h>` 与 `<bits/ioctl.h>`
中提供全套宏,导致大量跨平台代码默认"这些宏到处都有"。

musl 只实现 POSIX 必需部分:

- 不提供 `<termio.h>`(musl 1.1.15+ 移除);
- 其 `bits/ioctl.h` 可能定义部分 TC* 宏,但**不保证全套**,且不提供 BSD 名
  (TIOCGETA/TIOCSETA);
- aarch64 musl/OHOS 等平台上,代码引用的宏在编译期直接报 undeclared
  identifier。

错误出现在**使用点**而非定义点——若代码用 `#define TCGETA TIOCGETA` 回退,
则宏展开后引用的 TIOCGETA 才是爆炸点(见 DRAFT-E565 的宏重定义机制)。

## 解决方案

### 推荐方案(编译期能力守卫)

针对**每个具体缺失宏**加编译期能力守卫,仅隔离不可用的 legacy termio 分支,
保留 POSIX termios 路径完全可用:

```c
// legacy System V termio 分支 — 仅当宏真实存在时编译
#ifdef TCGETA
    /* ... TCGETA/TCSETA 用法 ... */
#endif

// 回退别名场景:守卫防止重定义 + 引用不存在的 BSD 名
#ifndef TCGETA
#define TCGETA TIOCGETA   /* glibc/macOS 走这里 */
#endif
```

lci 1.1 实例(src/run.c):

```diff
+// musl (OHOS) already defines TCGETA/TCSETA in bits/ioctl.h
+#ifndef TCGETA
 #define TCGETA TIOCGETA
+#endif
+#ifndef TCSETA
 #define TCSETA TIOCSETA
+#endif
```

补丁: `archives/l/lci/1.1/patches/0001-guard-termios-tcgeta-tcseta-musl.patch`

### 禁止做法

- ❌ **伪造宏**:`#define TCSETAF 0x5407` 之类凭空定义 ioctl 请求号——掩盖
  真实平台能力,数值可能错,且不可审计;
- ❌ **硬编码数值**:CFLAGS 加 `-DTIOCGETA=0x5405` 把 ioctl 数值烧进构建参数
  (DRAFT-E565 的 fallback 方案经复审违反本原则,故立本条目);
- ❌ **跳过全部终端功能**:`#if 0` 掉整个终端模块或 `--without-termios` 式
  裁剪——丢失 POSIX termios 可用路径,用户功能静默降级;
- ❌ 整体假定"musl 无任何终端 API":musl 有完整 POSIX termios,只需隔离
  legacy 分支。

### 验证

```bash
# 确认 sysroot 中宏的真实存在性
grep -rn "define TCGETA\|define TIOCGETA" <sysroot>/usr/include/
# 确认 termio.h 缺失
echo '#include <termio.h>' | clang --target=aarch64-linux-musl -E -x c - >/dev/null \
  || echo "termio.h absent"
# 修复后全链路验证(本仓实例):上游定义4项测试;OHOS构建注册并执行3项,3/3通过;
# 条件性valgrind测试因目标环境无可用Valgrind而未注册;消费者测试 1/1 + 鸿蒙特有测试 1/1
```

## 关联条目

- 相关: DRAFT-E565(同一 lci 1.1 补丁首次记录的宏重定义编译错误机制;
  本条目是其方法论升级:覆盖全部 TC* 宏族 + 明确禁止伪造/硬编码/跳过功能
  + 以保留 POSIX termios 路径为核心原则)
- E272(/bin/stty 部署问题,运行期,不涉及编译期宏)

## 证据

- 补丁: `archives/l/lci/1.1/patches/0001-guard-termios-tcgeta-tcseta-musl.patch`
  (Upstream-Status: Inappropriate [OHOS/musl specific])
- 验证: OHOS aarch64 自-hosted 真机,上游定义4项测试;OHOS构建注册并执行
  3项,3/3通过;条件性valgrind测试因目标环境无可用Valgrind而未注册;消费者测试
  1/1(3 场景/7 断言)、鸿蒙特有测试 1/1(6 检查点)全通过
- musl termio 移除背景: musl 1.1.15 changelog

## 元信息

- authors: Awstme(contributor_id: AWST)
- source_event: lci 1.1 OHOS aarch64 conan create(2026-09-09 整改复审)
- draft: true — 待主编审核后 promote 为正式 E 条目

## 与相似正式条目的区别

- **E171**：处理 `euidaccess` 缺失，并以 OpenHarmony 提供的等价接口
  `eaccess` 替换；E567 面对的是不存在可移植等价值的 legacy terminal
  ioctl request，不能执行直接名称替换。
- **E500**：以 POSIX 明确定义的 `_POSIX_MAX_INPUT` 补充缺失的
  `MAX_INPUT`，替代值具有标准语义依据；`TCGETA/TCSETA*` 的数值属于
  平台 ABI，不能套用同类兼容宏方案。
- **E211**：以可用的 `sched_getaffinity/sched_setaffinity` 替代缺失的
  pthread affinity 扩展；E567 不存在安全替代接口，只能在编译期检测能力，
  隔离 legacy `termio` 分支并保留 POSIX `termios` 主路径。
- **E565**：记录回退宏继续引用不存在标识符的具体编译错误；E567 进一步沉淀
  修复边界：禁止伪造终端 ioctl 宏、禁止硬编码 request 数值、禁止跳过终端功能，
  应以能力守卫实现分支隔离。
