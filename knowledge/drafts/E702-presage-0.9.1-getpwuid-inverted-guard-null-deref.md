# E702 人类可读文档 — get_user_home_dir() getpwuid 判空反写 → OHOS 必崩

> 配对 kv：`knowledge/drafts/E702-presage-0.9.1-getpwuid-inverted-guard-null-deref.kv`
> 实证任务：presage 0.9.1（任务卡 9711，`feat/presage-0.9.1`，2026-09-24）

## 现象

`make check` 中 `coreTestRunner` 打出 14~17 个点后
`Signal 11 (core dumped)`；手工单跑 `ProfileTest` / `ProfileManagerTest`
各自第 2 个点位附近 SIGSEGV。gdb 不可用（OHOS SELinux 拒绝 ptrace）。

## 定位手法（无调试器三步）

1. **逐 suite 二分**：写驱动按 `Suite::suite()` 单跑 11 个 suite → 收敛到
   `ProfileTest` 与 `ProfileManagerTest` 两个。
2. **SIGSEGV handler + backtrace**：驱动里 `signal(SIGSEGV, handler)` +
   `backtrace/backtrace_symbols_fd`（链接 `-rdynamic`）→ 栈顶
   `ProfileManager::get_user_home_dir()+0x88`。
3. **-O0 -g -no-pie 重建嫌疑 TU** 再取栈 + `addr2line` →
   `src/lib/core/profileManager.cpp:235`。

## 根因

```cpp
my_passwd = getpwuid (me);
if (!my_passwd) {                 // ← 写反了
    /* got passwd for user */     // 注释：拿到 passwd 才读
    result = my_passwd->pw_dir;   // NULL 解引用点
} else {
    /* unable to get passwd struct, read $HOME env variable */
    ... getenv("HOME") ...
}
```

- OHOS 无 passwd 数据库 → `getpwuid()` 返回 NULL → 每次 ProfileManager
  构造必崩（setUp/运行时都中）。
- 常规 Linux `getpwuid` 命中 → 走 else 读 `$HOME` → 永远不触发。上游与
  Debian 打包全绿，**平台差异把 bug 藏到移植才暴露**。
- “崩溃点 14/17 漂移”是静态注册序 + 手工环境缺 `srcdir`（`ProfileTest::setUp`
  的 `getenv("srcdir")`→`std::string(NULL)` 是另一处 UB，automake
  `check-TESTS` 会 `export srcdir` 所以 make check 下不出现）叠加的表象，
  不是非确定性。

## 修法（上游逻辑 bug 修复，一行）

```diff
-    if (!my_passwd) {
+    if (my_passwd) {
```

presage 实测：补丁后 `coreTestRunner` 31/31、`profileManagerTest` 2/2、
`make check` 9 个 automake 单元全绿。经 refresh-patch 两面登记为
`patches/0003-src-lib-core-profileManager.cpp.patch`。

## 复现/判据

```sh
# 源码层命中
grep -n "if (!my_passwd)" src/lib/core/profileManager.cpp
# 平台层：getpwuid 必 NULL
python3 -c "import pwd,os
try:
    pwd.getpwuid(os.getuid()); print('passwd OK')
except KeyError:
    print('NO PASSWD ENTRY -> getpwuid NULL')"
# 现象层
grep -n "Signal 11" $HOME/tmp/presage-0.9.1/w0/native-build.log
```

## 禁用做法

`--host=/--build=` 交叉参数绕过不触碰 getpwuid 逻辑（崩溃照旧），且丢掉全部
`AC_RUN_IFELSE` 检测面（E011 forbid 同款理由）。

## 推广

凡「`getpwuid` 优先、`$HOME` 兜底」的取 home 模式，先核对判空方向：**指针
非空才解引用**。移植到无 passwd 平台（容器、OHOS、distroless）前用上面的
python3 一行探针判命中面。
