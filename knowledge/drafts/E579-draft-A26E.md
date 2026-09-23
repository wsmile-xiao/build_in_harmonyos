# E579：musl/OHOS libc 保留 `L_cuserid` 宏但不声明也不导出 `cuserid()`

> Contributor: Awstme <awstme@qq.com> | Status: Draft | Updated: 2026-09-11
> Source: coolmail 1.3 OHOS 适配（设备 conan create 首轮编译失败 → 补丁 → 全绿）

## 错误特征

1990 年代风格的 C 代码在 OHOS clang 15（C99+）下编译时报（一手日志逐字留档于本 PR 的
`archives/c/coolmail/1.3/reports/upstream-compile-failure-log.md`，其原始 `.log` 的 sha256
`d21452210b92f79ca950ff6168618b85f52453bfafa550dd21ce5d5cdb61d32b`、退出码 1）：

```text
coolmail.c:107:4: warning: call to undeclared library function 'strcat' with type
    'char *(char *, const char *)'; ISO C99 and later do not support implicit
    function declarations [-Wimplicit-function-declaration]
   strcat(mailfile_str, cuserid(username));
   ^
coolmail.c:107:25: warning: call to undeclared function 'cuserid'; ISO C99 and later
    do not support implicit function declarations [-Wimplicit-function-declaration]
coolmail.c:107:25: error: incompatible integer to pointer conversion passing 'int' to
    parameter of type 'const char *' [-Wint-conversion]
6 warnings and 1 error generated.
```

复现命令（对**未打补丁**的上游源码，只编译单个目标文件）：

```sh
python3 -c "import tarfile; tarfile.open('coolmail-1.3.tar.gz').extractall('.')"
cd coolmail-1.3
clang -O2 -I<libxt>/include -I<libx11>/include -I<libxsm>/include \
      -I<libice>/include -I<xorgproto>/include -c coolmail.c -o /dev/null
```

注意症状的形态：`char username[L_cuserid];` 这一行**编译通过**（宏还在），
失败点在同一条语句里的函数调用。同一份日志还在 `coolmail.c:469:4` 报
`call to undeclared function 'disp_sync'`（缺 `display_list.h` 声明）、在
`coolmail.c:352`/`coolmail.c:355` 报 `strcmp`/`strncpy` 隐式声明——三处根因同族。

## 触发条件

- 构建系统: 任何（本例为手写 GNU Makefile）
- 阶段: 编译（compilation）
- 前提: 源码用 `cuserid(buf)` 取登录名；`<string.h>` 等标准头被放在
  可选特性的 `#ifdef` 里（本例 `#ifdef AUDIO`），该特性关闭后字符串函数全部走隐式声明

## 根因分析

OHOS musl 的三处事实互相矛盾，必须三处一起核对：

| 探测 | 结果 |
|------|------|
| `grep -rn 'L_cuserid' $SYSROOT/usr/include/stdio.h` | `#define L_cuserid 20`（**宏保留**） |
| `grep -rn 'cuserid' $SYSROOT/usr/include/` | 只有上面那行宏，**没有任何函数声明** |
| `nm -D $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so \| grep -i cuserid` | **空**（动态库不导出） |
| `nm $SYSROOT/usr/lib/aarch64-linux-ohos/libc.a \| grep -i cuserid` | `cuserid.o: 0000000000000000 T cuserid`（**只在静态归档里**） |

于是：

1. `char buf[L_cuserid];` 合法 → 误以为接口可用；
2. `cuserid(buf)` 无声明 → 按 C89 规则隐式声明为 `int cuserid()`，实参 `int`
   传给 `strcat` 的 `const char *` → clang 直接报硬错误（`-Wint-conversion`）；
3. 即使手工补 `extern char *cuserid(char *);` 让编译期过关，**动态链接仍然失败**：
   符号在 `libc.so` 中不存在，只有静态链接 `libc.a` 才能解析。这是本条与普通
   “缺头文件” 类问题的关键区别。

`cuserid()` 本身在 POSIX.1-2001 就被删除，glibc 只是作为过时接口继续提供；
musl 系（含 OHOS）选择不导出。老代码依赖的是编译器对隐式声明的容忍度，
而不是 libc 的实际保证。

## 解决方案

### 推荐方案

源码可移植性补丁（glibc/musl 通用、可向上游提交，P005）：

```c
/* 删除 char username[L_cuserid]; 与 strcat(mailfile_str, cuserid(username)); */
{
   struct passwd *pw = getpwuid(getuid());
   char *name = NULL;

   if (pw != NULL && pw->pw_name != NULL)
      name = pw->pw_name;
   else if (getlogin() != NULL)
      name = getlogin();
   else if (getenv("LOGNAME") != NULL)
      name = getenv("LOGNAME");
   else if (getenv("USER") != NULL)
      name = getenv("USER");
   strcat(mailfile_str, (name != NULL) ? name : "unknown");
}
```

要点：

- **NULL 回退链不是装饰**：E338 实测 OHOS 上 `getpwuid()` 可以返回 NULL，
  不判空会直接把 NULL 交给 `strcat` 触发 SIGSEGV；
- 同时把被 `#ifdef` 包住的 `<string.h>` 改成无条件包含（否则关闭该特性后
  `strcat`/`strcmp`/`strncpy` 全部是隐式声明，在 clang 16+ 直接变硬错误）；
- 不引入 `__OHOS__` 条件编译，补丁对 glibc 同样成立。

### 禁止做法

- ❌ 手工补 `extern char *cuserid(char *);`（或自己写一个同名包装）：符号在
  `libc.so` 中不存在，问题只是从编译期推迟到动态链接/运行期；
- ❌ 用 `-Wno-implicit-function-declaration` 或 `#pragma GCC diagnostic ignored`
  压制：指针被按 int 截断属 UB，且掩盖真正的缺头文件问题。

## 验证

```bash
# 1. 三处 libc 事实核对（本包实测输出见上表）
SYSROOT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot
grep -rn 'L_cuserid' "$SYSROOT/usr/include/stdio.h"
nm -D "$SYSROOT/usr/lib/aarch64-linux-ohos/libc.so" | grep -i cuserid
nm "$SYSROOT/usr/lib/aarch64-linux-ohos/libc.a" | grep -i cuserid

# 2. 补丁后干净构建 + 消费者测试（本包实测：conan create EXIT=0；7 项断言全过）
conan create archives/c/coolmail/1.3 -pr:h "$HOST_PROFILE" -pr:b "$HOST_PROFILE"
```

## 关联条目

- 相似: E534（OHOS musl 缺失 GNU/BSD 扩展函数 → 隐式声明，BusyBox 兼容层）
- 相似: E338（OHOS `getpwuid()` 返回 NULL 导致 SIGSEGV —— 本方案必须判空的原因）
