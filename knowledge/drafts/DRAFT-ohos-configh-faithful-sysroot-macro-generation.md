# DRAFT-ohos-configh-faithful-sysroot-macro-generation：手写最小 config.h 致测试假失败——按 sysroot 逐宏双重验证忠实生成

> Contributor: xiao921924 | Status: Draft | Updated: 2026-09-03
> Source: burp 3.3.0 HarmonyOS PC 适配（最小 config.h 致 2 个上游用例假失败）

## 现象

移植 autotools 库时手写"最小 config.h"（只含基础宏）编译通过，但上游
测试套件里出现一批"看似逻辑 bug"的失败：

```
FAIL: test_check_passwd      （依赖 HAVE_CRYPT 的校验路径被编译关闭）
FAIL: test_lock_simple_failure （依赖 HAVE_LOCKF 的锁路径被编译关闭）
```

失败断言与某个特性开关一一对应——不是代码 bug，是特性被 `#ifdef HAVE_*`
静默关掉了。sysroot 实际具备这些能力，但 config.h 没定义对应宏。

## 与现有知识的关系

- 现有索引中 config.h 相关条目（E025/E040/E061/E151/E284/E309/E387）
  全是**单宏个案**（某个宏缺/错），无"忠实生成方法论"条目。
- 本条是方法论级知识：如何系统性生成忠实 config.h，而非逐个救火。

## 方案

1. 从 `configure.ac` 提取全部探测宏清单（AC_CHECK_FUNCS/HEADERS/
   LIBS、AC_SEARCH_HEADERS 等）。
2. 对每个候选宏做**双重验证**：
   - (a) 头文件层：sysroot 对应头文件/函数声明存在；
   - (b) 符号层：`readelf --dyn-syms <sysroot>/.../libc.so` 中该符号可见
     （静态库则看对应 .a 的 nm 输出）。
   - 两者都过才 `#define`；任一层不过就不定义。
3. sysroot 确实不具备的能力（OHOS 无 chflags/acl/ncurses/systemd/libcap）
   保持不定义，让代码正确编译出特性关闭态——**不靠猜测开宏**（开错比
   漏掉危害大：编译过但运行时 undefined symbol）。
4. 每个宏的验证证据（命令 + 关键输出）写入 notes.md「遇到的问题与
   解决方案」，可复核。
5. 生成 config.h 后重跑上游套件，**对比修复前后失败集合**——被救回的
   用例就是方法论有效性的直接证据。

## 验证证据

- burp 3.3.0：补 `HAVE_CRYPT` / `HAVE_LOCKF` / `HAVE_BLAKE2` / `HAVE_XATTR`
  等宏后，`test_check_passwd`、`test_lock_simple_failure` 由 FAIL 转 PASS
  （救回 2 例）；OHOS 无 chflags/acl/ncurses/systemd/libcap，对应宏
  不定义，其余 233 例结果不变（无副作用）。
- 适用软件：所有需手写/生成 config.h 的 autotools 库移植（tarball 无
  预生成 configure、或 conan 无法跑 autogen 的场景）。
