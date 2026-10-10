# OHOS musl 缺传统 tty 头 `<termio.h>` 与 HZ 节拍宏——构建期切换 + 特性守卫

> 知识条目：`knowledge/drafts/DRAFT-xmcd-3.3.2-ohos-musl-missing-termio-and-hz.kv`
> 拓展包（检测脚本 + 复现脚本 + README）：`knowledge/drafts/musl-pthread-cancel-gap/`
> 样例库：`archives/x/xmcd/3.3.2`（补丁 `patches/0003-common_d-config.h.patch`）

## 1. 现象

老代码在 OHOS aarch64（clang 15 / musl）上构建时：

```
fatal error: 'termio.h' file not found          # System V 传统 tty 头
error: use of undeclared identifier 'HZ'         # 传统内核节拍宏
```

两者常同时出现（同一批 1980s–1990s 代码的平台配置头与 ioctl 换算逻辑）。

## 2. 根因（实测证据）

| 探针（2026-10-04，OHOS SDK 26.0.0.18 sysroot） | 结果 |
|---|---|
| `#include <termio.h>` 语法检查 | **No such file or directory**（musl 只有 `<termios.h>`） |
| 源码平台分支默认值（样例 `common_d/config.h`） | `#if defined(_LINUX)` → `#define USE_TERMIO` |
| `HZ` 使用者（样例 `libdi_d/os_linux.c`） | `jiffies = (unsigned long) tmout * HZ;`（`ioctl(SG_SET_TIMEOUT)` 路径） |

`HZ` 在 glibc 环境常由 `<sys/param.h>` / 内核头间接带入，musl 不定义；`<termio.h>`
则是 System V 传统接口头，musl 有意不提供（POSIX 接口为 `<termios.h>`）。

## 3. 处置（首选策略）

**构建期切换 + 平台头特性守卫**（不复制替代头、不改系统头）：

```c
/* common_d/config.h —— 让"调用方能否选 termios"成为显式能力,缺省不变 */
#if defined(_LINUX)
#  ifndef USE_TERMIOS
#    define USE_TERMIO        /* 上游缺省:musl 下由 -DUSE_TERMIOS 覆写 */
#  endif
#endif
```

```sh
# 配方注入（样例 conanfile.py）
CFLAGS="$CFLAGS -DUSE_TERMIOS -DHZ=100"
```

- `-DUSE_TERMIOS`：老代码多自带 `USE_TERMIOS/USE_TERMIO` 双分支，切到 POSIX 分支即可；
- `-DHZ=100`：仅影响"秒 → jiffies"的换算（传统 UNIX 取值 100），不改变 ioctl 语义。

## 4. 禁止做法

1. **复制外来 `<termio.h>` 进源码树**——结构体布局与 ioctl 常数（`TCGETA` 等）与 musl
   的 termios 混用，编译过、运行期 `EINVAL`/结构体错乱；
2. **宏别名硬替换**（`-Dtermio=termios` / `#define termio termios`）——掩盖成员名与
   常数差异，属"编译过但语义错"的假修复。

## 5. 验证

- 直线验证：`conan create archives/x/xmcd/3.3.2`（ohos-aarch64 profile）全绿，W3
  exit_code=0；
- 反向验证：去掉 `-DUSE_TERMIOS` 恢复 `termio.h` 缺失报错；去掉 `-DHZ=100` 恢复
  `use of undeclared identifier 'HZ'`；
- 运行验证：`cda -h` 输出横幅与用法（终端路径不崩），`xmcd -h` 抵达显示初始化。

## 6. 关联

- 同批处置（同一 PR）：`DRAFT-xmcd-3.3.2-ohos-musl-missing-pthread-cancel.*`
  （线程取消 API 缺口，同一 musl 精简选择的不同侧面）
- 拓展包总览：`knowledge/drafts/musl-pthread-cancel-gap/README.md`
- BSD 遗留函数族：`DRAFT-xli-1.17.0-ohos-musl-missing-rindex-bsd-legacy.*`
