# E900 — 旧式 C 源码缺 `<time.h>`：`ctime`/`gmtime` 隐式声明在 aarch64 上截断指针，编译只告警、运行时段错误

## 错误特征

编译日志（通过，仅告警）：

```
news.c:278:34: warning: call to undeclared function 'ctime'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
news.c:292:38: warning: call to undeclared function 'gmtime'; ...
news.c:292:10: warning: call to undeclared function 'strftime'; ...
news.c:429:6:  warning: call to undeclared function 'time'; ...
```

运行时（qemu-aarch64，同源 `.o` 以 `-static-pie` 重链）：

```
[4] -d adds strftime datestamp
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
```

`--version` / `--help` 这类冒烟测试全部正常，只有 `-a`（`ctime`）、`-d`（`gmtime`+`strftime`）、`-e`（`time`）路径崩溃。

## 触发条件

- 构建系统: Makefile / Autotools 均可
- 阶段: 编译（告警）→ 运行（SIGSEGV）
- 源码特征: 老式 C，`#include` 里没有 `<time.h>`，却调用返回指针的 time 系函数

## 根因分析

C89 允许隐式声明，返回值按 `int` 处理。clang 15 对此只发 `-Wimplicit-function-declaration` 告警。在 LP64（aarch64/x86_64）
的 PIE/动态可执行文件里，`ctime()` 返回的高位地址被截断为 32 位再符号扩展，作为 `%s` 参数或 `struct tm *`
使用时立即崩溃。x86 非 PIE 静态链接时地址小于 4GB，截断后仍然有效，所以问题容易被“碰巧通过”的环境掩盖——
本次适配中 `-static`（非 PIE）重链的 aarch64 二进制无补丁也能 ALL PASS，必须用 `-static-pie` 才能复现。

## 解决方案

### 推荐方案

给出问题的 `.c` 增加缺失的标准头，用 `refresh-patch --auto` 生成补丁（本例 `0001-news.c.patch`，仅加一行 `#include <time.h>`，无平台宏）。

### 禁止做法

- ❌ `-Wno-implicit-function-declaration` / `-std=gnu89`：只压告警，隐式 int 仍在
- ❌ 手写 `extern char *ctime();` 原型或 `#ifdef __OHOS__` 守卫：复制 libc ABI、带平台宏（R8/PF5）

## 验证

```bash
clang -Wall -O2 -c news.c 2>&1 | grep -c "undeclared function"    # 补丁后应为 0
# 补丁前/后各做一份 static-pie 重链，在 qemu-aarch64 下运行 test_package/test.sh：
clang -fPIE -static-pie -Wl,-z,muldefs -o news news.c getopt.c ...
PATH=$PWD/bin:$PATH bash test.sh ./check_news   # 补丁前 rc=1(SIGSEGV)，补丁后 ALL PASS
```

## 关联条目

- 相关: E420（同为旧式 C 隐式 int，但那条是依赖头拆分导致的编译期错误；本条是 libc 标准头缺失导致的运行期指针截断）、E063、E093
