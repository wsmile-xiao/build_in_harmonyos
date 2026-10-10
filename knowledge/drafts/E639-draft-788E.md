# E639 — OHOS `<utmp.h>` 只有 utmp API 子集：`getutline()`/`getutid()` 无声明、`libc.so` 不导出

> **Status**: Draft（待主编审核 promote）｜ **severity**: 2 ｜ **category**: musl, libc, portability, headers
> **来源实例**: ttysnoop 0.12d（`ttysnoops.c` 的 `cleanup_utmp()`）｜ **对应 kv**: `knowledge/drafts/E639-draft-788E.kv`

## 错误特征

```
ttysnoops.c:373:11: warning: call to undeclared function 'getutline'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
ttysnoops.c:373:9: error: indirection requires pointer operand ('int' invalid)
```

补上 `struct utmp *getutline(const struct utmp *);` 后：

```
ld.lld: error: undefined symbol: getutline
```

再改成 `-static` 链接：能链接、能启动，程序退出时被 **SIGSEGV（signal 11）** 杀死。

## 触发条件

- 构建系统：任意（本例为裸 Makefile），工具链 OHOS SDK clang 15.0.4 / aarch64-unknown-linux-ohos
- 阶段：编译（隐式声明）→ 链接（`libc.so` 无符号）→ 运行（musl utmp 桩返回 NULL）
- 代码形态：`utmp = *(getutline(&utmp));` 或 `getutid()` 结果不判空直接解引用

## 根因分析

1. **头文件**：`sysroot/usr/include/utmp.h` 通过 `#define utmp utmpx` 映射到 utmpx，只声明
   `endutent/getutent/pututline/setutent/utmpname/login_tty`；`getutline`/`getutid` 在
   `utmp.h`、`utmpx.h` 里都没有声明。
2. **动态库**：`libc.so` 只导出 `setutent/getutent/pututline/endutent/utmpname`；
   `getutline/getutid/getutxline/pututxline/setutxent/endutxent` 只在静态 `libc.a` 里。
3. **运行语义**：musl 的 utmp 是桩（`_PATH_UTMP` = `"/dev/null/utmp"`），读接口恒返回 NULL。
   所以即便静态链接成功，不判空的解引用也会崩溃；glibc 上“找不到匹配项”时同样返回 NULL，
   只是平时不触发——这是上游潜伏缺陷，OHOS 把它变成了必现。

报错落在“解引用”而不是“缺声明”，容易被误判成类型或结构体问题；先看同一行的
`call to undeclared function` 警告。

## 解决方案

### 推荐方案：`getutent()` 扫描 + 判空（不引入平台宏）

```c
struct utmp *ut, entry;

setutent ();
while ((ut = getutent()) != NULL)
	if ((ut->ut_type == LOGIN_PROCESS || ut->ut_type == USER_PROCESS)
	    && strncmp(ut->ut_line, line, sizeof(ut->ut_line)) == 0)
	{
		entry = *ut;           /* 与 getutline() 语义一致：只匹配 LOGIN/USER_PROCESS */
		*entry.ut_user = 0;
		pututline (&entry);
		break;
	}
endutent ();
```

`getutent/pututline/setutent/endutent` 在 OHOS 头文件里有声明、`libc.so` 有导出；
glibc 上行为与原代码相同，补丁可向上游提交。

### 回退方案

utmp 记账与核心功能无关时，整段删除（等价 `OMIT_UTMP`，参见 E121），并在 notes 写明平台 utmp 为桩。

### 禁止做法

- ❌ 手工补 `getutline()` prototype：只把错误推迟到链接期（`libc.so` 无此符号）。
- ❌ 为让 `getutline` 从 `libc.a` 解析而整体 `-static`：交付物脱离系统 `libc.so`，且退出时解引用 NULL 崩溃。
- ❌ `-Wno-implicit-function-declaration` 压告警：隐式 `int` 返回值截断指针，问题只会更隐蔽。

## 验证

```bash
SR=$NDK/sysroot; L=$SR/usr/lib/aarch64-linux-ohos
grep -n 'getut' $SR/usr/include/utmp.h $SR/usr/include/utmpx.h        # 只有 getutent
llvm-nm -D --defined-only $L/libc.so | grep -wE 'getutline|getutid|getutent'   # 仅 getutent
llvm-nm --defined-only $L/libc.a  | grep -wE 'getutline|getutid'               # 静态归档里有
```

本例实测（qemu-aarch64，同源 `.o` 静态重链、非特权用户运行消费者测试
`archives/t/ttysnoop/0.12d/test_package/test_ttysnoop.c`）：

| 变体 | 结果 |
|------|------|
| 旧写法 + 手工 prototype，动态链接 `libc.so` | `ld.lld: error: undefined symbol: getutline` |
| 旧写法 + 手工 prototype，`-static` | 用例 9、16 失败：`ttysnoops ... killed by signal 11` |
| 推荐方案（本包补丁 0004） | 16/16 通过，`ttysnoops` 退出码 0 |

## 关联条目

- 相似：E121（utmpx 族 `setutxent/pututxline/endutxent` 链接失败，走 `OMIT_UTMP`）
- 相似：E579 草稿（`cuserid()`：头文件无声明、`libc.so` 不导出、仅 `libc.a` 有——同一“静态有、动态无”形态）
- 相关：E429 草稿（`utmpx.h` 只声明 `struct utmpx`）
