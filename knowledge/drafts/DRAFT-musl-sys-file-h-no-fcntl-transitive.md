# DRAFT: musl <sys/file.h> 不透传 fcntl 声明——F_GETFL/F_SETFL/O_* 须直接包含 <fcntl.h>

- **草稿 ID**: DRAFT-musl-sys-file-h-no-fcntl-transitive
- **来源库**: l2tpns 2.5.0（OHOS PC aarch64, clang 15.0.4 / OHOS SDK 26.0.0.18, HongMeng 内核；musl libc）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **严重度**: L1（musl 目标上确定性编译失败，glibc 上不可见）

## 问题（真机实测）

多个只包含 `<sys/file.h>` 的 C 翻译单元直接使用 fcntl 命令字与文件状态标志
（`F_GETFL`、`F_SETFL`、`O_NONBLOCK`、`O_RDONLY`、`O_DIRECTORY`）。
glibc 的 `<sys/file.h>` 会聚合透传 `<fcntl.h>` 的接口声明，编译通过；
musl 的 `<sys/file.h>` 只提供 `flock`/`lockf`/`LOCK_*` 等文件锁接口，
**不包含任何 fcntl 命令字或 O_* 宏**，clang 报
`error: use of undeclared identifier 'F_GETFL'`（每个标识符一处、逐处计数）。

l2tpns 2.5.0 真机首轮编译即命中两文件共 11 处：

- `cli.c`：5 处（F_GETFL/F_SETFL/O_NONBLOCK 各 1 + O_RDONLY/O_DIRECTORY 组合 1 行 2 处）
- `cluster.c`：6 处（F_GETFL/F_SETFL/O_NONBLOCK 两组）

证据：本 run 设备日志 `/storage/Users/currentUser/tmp/oh-device-porting-v2/l2tpns-2.5.0/manual-make.log`
（cli.c:298/301/333 等 5 error）与 `manual-make2.log`（cluster.c:119/122/210/213 等 6 error）。

## 根因

"包含什么头文件得到什么声明"是 libc 实现细节，不是 C 标准承诺：

- glibc：`sys/file.h` 内部 `#include <fcntl.h>`（隐式透传），长期纵容了
  "用 flock 顺带用 fcntl"的写法；
- musl：`sys/file.h` 严格限定文件锁职责，fcntl 家族只从 `<fcntl.h>` 暴露。

凡在 glibc 上"碰巧编译通过"的间接包含，移植到 musl（含 OHOS SDK sysroot）
时确定性失败——且失败点在**使用处**而非包含处，跨文件扩散时排查面大。

## 方案（推荐：逐文件补直接包含）

凡使用 `fcntl()` 命令字（F_GETFL/F_SETFL/F_SETFD…）或 `open()` 状态标志
（O_*）的翻译单元，直接 `#include <fcntl.h>`（"include what you use"）。
最小、可解释、对 glibc 无副作用（重复包含被 include guard 吸收）。

l2tpns 落地：`patches/0002-fcntl-include.patch`——在 `cli.c`/`cluster.c` 的
`#include <sys/file.h>` 之后插入 `#include <fcntl.h>`，`patch -p1` 应用。

### fallback（源码不可改时）

构建期强制注入：`EXTRA_CFLAGS=-include fcntl.h`（或配方层等价机制）对全部
翻译单元生效；代价是掩盖"哪些文件缺包含"的精确信息，且对仅作 force-include
用途的头必须确保幂等。仅在无法产出源码补丁时使用。

## 验证（两行编译探针，musl 目标下执行）

```sh
printf '#include <sys/file.h>\nint p(int fd){return fcntl(fd, F_GETFL);}\n' > p1.c && ${CC:-clang} -c p1.c -o /dev/null   # 期望失败: use of undeclared identifier 'fcntl' / 'F_GETFL'
printf '#include <sys/file.h>\n#include <fcntl.h>\nint p(int fd){return fcntl(fd, F_GETFL);}\n' > p2.c && ${CC:-clang} -c p2.c -o /dev/null   # 期望通过
```

第一条在 musl 上必失败、glibc 上通过，即本条目的判别特征；补包含后第二条
在两个 libc 上均通过。

## 适用边界

- 所有在 glibc 上只经 `<sys/file.h>`（或类似聚合头）间接获得 fcntl 声明的
  C/C++ 源；网络/守护进程类软件设置非阻塞 IO（F_GETFL|O_NONBLOCK）是高频命中面。
- 同族判别：任何"glibc 聚合头透传、musl 严格分头"的声明集合
  （`sys/file.h`→fcntl；`sys/types.h` 不给 stdint 等）。

## 反例与限制

- **禁止手抄宏值**（`#define F_GETFL 3`、`#define O_NONBLOCK 0x4000` 等）：
  这些是平台 ABI 常量，跨 libc/架构不保证稳定，手抄等于把实现细节固化进源码；
- **禁止**依赖 `_GNU_SOURCE`/`__USE_MISC` 等 glibc 特性宏试图让 musl 的
  `<sys/file.h>` "漏出" fcntl 声明——musl 无该机制，纯无效方向；
- 修包含后不应顺手改动其余包含结构（最小补丁原则）。

## 查重差异

- 与 **E119**（OHOS 净化版 uapi 头与 musl/libc 头的类型重复冲突，batctl 同族）
  同属"OHOS 头文件生态与 glibc 语义差异"，但 E119 是**类型重复定义**
  （include guard 不互斥），本条是**声明缺失**（聚合头不透传）——一个要"跳过"，
  一个要"补包含"，方向相反，不构成重复；
- 与 E063（-Werror 升级告警为错误）不同域：本条是硬编译错误而非告警升级。

## 参考

- musl `include/sys/file.h`、`include/fcntl.h`（musl-libc 源码树）
- glibc `misc/sys/file.h`（含 `#include <fcntl.h>` 透传）
- 本仓库归档：`archives/l/l2tpns/2.5.0/patches/0002-fcntl-include.patch`
