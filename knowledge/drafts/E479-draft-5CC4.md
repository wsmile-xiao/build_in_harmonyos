# E479 — 文件系统权限语义不可靠时优先用上游自带开关，而不是跳过测试

## 错误特征

上游用例把文件 `chmod 000` 后访问，期望得到「权限不足」的行为；在鸿蒙真机上
访问依旧成功，于是用例失败。上游代码（`test/unit_test.c:1097` 起，
守卫为 `#if !defined(TEST_UNDER_VIRTUALBOX) && !defined(_WIN32)`）：

```c
system("touch test_unreadable; chmod 000 test_unreadable");
ns_printf(nc, "GET /%s HTTP/1.0\n\n", "../test_unreadable");
...
ASSERT_STREQ_NZ(status, "HTTP/1.1 500");   /* unit_test.c:1121 */
```

真机实测（未加守卫开关时逐字照抄）：

```
Expected: HTTP/1.1 500
Actual  : HTTP/1.1 200
unit_test.c:1121:1 [ASSERT_STREQ_NZ(status, "HTTP/1.1 500")] (in test_http_errors)
FAIL, run 3 in 0.145s
```

底层文件系统核对见「根因分析」的 8 数据点表。

## 触发条件

- 构建系统: makefile / cmake / autotools 均可能（与构建无关，属运行期文件系统语义）
- 阶段: testing —— 断言依赖 POSIX 权限、只读目录、rename 覆盖、符号链接等语义的用例

## 根因分析

HMDFS 上 `chmod()` **调用成功但只加不减**，且脚本无法从返回码发现：真机实测
（`$HOME/tmp`，文件系统 `hmdfs`，8 个数据点全部 `rc=0`）：

| 请求模式 | 结果模式 | 读取 |
|---|---|---|
| `chmod 000` | `-rw-r-----` | OK |
| `chmod 400` | `-rw-r-----` | OK |
| `chmod 600` | `-rw-r-----` | OK |
| `chmod 644` | `-rw-r-----` | OK |
| `chmod 040` | `-rw-r-----` | OK |
| `chmod 004` | `-rw-r-----` | OK |
| `chmod 700` | `-rwxr-----` | OK，可执行 |
| `chmod 755` | `-rwxr-x---` | OK，可执行 |

即有效模式 = `创建时模式 | 请求模式`，且 **world 位永远为 0**：
`umask 000` 下新建文件仍是 `-rw-rw----`，随后 `chmod 000`/`chmod 400` 都改不动。
目录另有规则（`mkdir d; chmod 000 d` → `drwxrws--x`）。三条后果：

1. **无法把文件变成不可读**，所以「改权限后访问应失败」这类断言在该平台必然不成立。
2. `chmod` 恒返回 0，`os.access(X_OK)` 同样不可信（R49 的「三个禁止」里已列出），
   因此探测式写法既不能作判据也不能用来兜底。
3. 只有「加执行位」这一类请求会生效 —— 反过来意味着任何依赖「去掉权限」的自检
   都会静默通过。

关键点：这类断言通常**嵌在一个更大的用例函数里**。直接跳过整条用例会连带丢掉同一
函数内其它仍然有效的断言，等于用环境问题换掉了真实覆盖。

## 解决方案

### 推荐方案：使用上游自带的「文件系统不可靠」开关

先在源码里找上游为不可靠文件系统预留的编译期开关，用构建参数传入，只关闭那一个
断言块，零源码改动。已知实例：

| 上游 | 开关 |
|------|------|
| Cesanta（fossa / mongoose） | `TEST_UNDER_VIRTUALBOX`（为 VirtualBox 共享文件夹等权限语义不可靠环境提供） |

其它项目按同一思路现场找，不要凭印象猜名字：

```sh
# 两种写法都要覆盖：`#ifdef X` / `#if !defined(X)`
grep -rnE "#if.*defined.*(SKIP|NO_[A-Z_]*TEST|SANITY|BOX|VIRTUALBOX|PERM)" test/ src/
# fossa 2.1 实测命中: test/unit_test.c:1108:#if !defined(TEST_UNDER_VIRTUALBOX) && !defined(_WIN32)
```

```sh
make -C test -j1 unit_test CC=$CC CFLAGS_EXTRA=-DTEST_UNDER_VIRTUALBOX
```

这样做同时满足三条约束：不改上游 `.c/.h`、补丁里不出现平台宏（R8/PF5）、
受影响的只有那一处断言块而非整条用例。

**先读开关到底圈住了什么，再决定用不用。** fossa 2.1 里另一个候选
`#ifndef NO_DNS_TEST`（`unit_test.c:1980`、`:3224`）只圈住 `test_resolve`，
而该用例在本环境本来就是 PASS —— 用它等于白白少跑一条有效用例。
真机 A/B 证实选定开关的粒度正好：

| 构建参数 | `./unit_test test_http_errors` |
|---|---|
| 不带开关 | `FAIL` —— `unit_test.c:1121`，`run 3`（期望 500 实得 200） |
| `CFLAGS_EXTRA=-DTEST_UNDER_VIRTUALBOX` | `PASS, run 5 in 0.021s` |

注意 `test/Makefile` 的 `unit_test` 目标不依赖 `CFLAGS`，改开关后必须
`rm -f test/unit_test` 再 make，否则 make 报 `up to date` 而静默复用旧二进制。

### 回退方案：确无上游开关时按 E046 跳过并归因

只有在上游没有可用开关时，才按 E046 跳过该用例，并给出真机实测证据
（`chmod 000` 后的 `ls -l` 与读取结果）以及被丢弃的断言数，让评审能看到代价。

### 禁止做法

- ❌ 在补丁里加 `#ifdef __OHOS__` 包住该断言 —— R8/PF5 补丁平台宏闸直接拦截，
  且该补丁永远无法进上游。
- ❌ 为了「让测试通过」改写断言期望值。
- ❌ 整组/整文件跳过，用一个跳过项掩盖多条无关断言。

## 验证

```sh
touch f && chmod 000 f && ls -l f && (cat f >/dev/null && echo READ_OK)
# HMDFS 上仍输出 -rw-r----- 且 READ_OK ⇒ 命中本模式
```

传入开关后重新运行该用例应得到 `PASS`；同时对照矩阵中该用例的断言数，
确认只减掉被守卫的那一条，其余断言仍在执行。

## 关联条目

- 相关: E046（HMDFS/SELinux 下 chmod 与 os.access 不可信 —— 本条把处置从「跳过」
  升级为「优先使用上游自带开关，仅在无开关时跳过并归因」）、E011、E087（同类 HMDFS 权限问题）
- 适用铁律: R8（补丁不得引入平台宏）、R49（禁止 `os.access(X_OK)` 探测）

## 来源

- 软件/版本: fossa/2.1（`archives/f/fossa/2.1`，`test_http_errors`）
- 上游: https://github.com/cesanta/fossa `test/unit_test.c:1108`
