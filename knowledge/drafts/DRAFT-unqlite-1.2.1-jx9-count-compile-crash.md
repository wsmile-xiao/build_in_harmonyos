# E-DRAFT: unqlite 1.2.1 Jx9 `count()` 编译期崩溃（Signal 11），脚本应用 foreach 迭代而非 count()

- **触发实例**：unqlite 1.2.1 适配（2026-09-18，任务 unqlite-1.2.1-r01-pc3-9，分支 feat/unqlite-1.2.1）
- **错误签名**：Jx9 脚本执行 `unqlite_compile()` 时进程直接 Signal 11（core dumped，退出码 139）
- **类别**：embedded-db / script-engine / runtime（Jx9 文档存储接口）
- **严重度**：2（运行时确定性崩溃，脚本层规避模式固定）

## 症状

在任意 unqlite 1.2.1 数据库句柄上编译含 `count()` 的 Jx9 脚本即崩溃：

```c
unqlite_open(&pDb, ":mem:", UNQLITE_OPEN_IN_MEMORY);
unqlite_compile(pDb, "print 'n=' . count([1,2,3]);", len, &pVm);  /* Signal 11，进程死亡 */
```

- 崩溃点：`unqlite_compile()` 内部（不进入 `unqlite_vm_exec()`），不区分 nByte 传 `-1` 或 `strlen`。
- 对照组（全部正常）：`print 'hello';`、`db_create('users')`、`db_store('users', $zRec)`、
  `db_fetch_all('users', $callback)` + `foreach` 迭代。
- 崩溃组合：`count([1,2,3])`（数组字面量）与 `count($data)`（db_fetch_all 结果数组）均复现。

## 根因

unqlite 1.2.1 的 Jx9 脚本引擎在编译处理 `count()` 内置函数（作用于数组表达式）时内部崩溃。
1.2.1 CHANGELOG 记录 SyMemBackend 池路径简化（`SyMemBackendPoolAlloc/Free` 改走普通后端并从
runtime 移除池分配器机制），疑为此回归引入点，但上游未提供 count 专项修复 commit。
**非 OHOS 平台问题**：用上游 amalgamation（unqlite.c）以 clang 直编（不经 Conan）在
aarch64 上同样复现；也排除消费者测试参数错误——上游官方样例 `samples/4.c` 全程使用
`foreach($data as $value)` 迭代而非 count()，运行正常（输出 Filtered records 3 条）。

## 规避方案（推荐）

Jx9 脚本中避免 `count()`（尤其数组字面量与 db_fetch_all 结果），改用 foreach 迭代：

```js
$zCallback = function($rec){ if( $rec.age < 30 ){ return FALSE; } return TRUE; };
$data = db_fetch_all('users',$zCallback);
foreach($data as $value){
  print $value..JX9_EOL;
}
```

替代后验证：消费者测试 test_unqlite.c 的 Jx9 段 6 项断言（打开 Jx9 内存库、
compile、config、exec、过滤输出、释放 VM；Jx9 API 主断言 5 项 + 内存库打开
1 项）与 OHOS 专项测试 test_unqlite_ohos.c 12 项磁盘持久化断言全部通过；
conan-verify G2（conan create 干净构建）PASS；上游 sample4.c 链接同一
libunqlite.a 运行正常。

## 适用边界

- 仅针对 unqlite 1.2.1 的 Jx9 接口；KV 引擎（unqlite_kv_*）不受影响（6 项 KV 断言全过）。
- 不含 count() 的任意 Jx9 脚本编译/执行均正常，不能由此断言语义"Jx9 整体不可用"。

## 反例（不适用场景）

- 脚本不含 count() → 正常，无需规避。
- 需要精确计数的业务：先 foreach 累计（`$n++`）再输出，避免 count()。

## 证据

- 最小复现脚本 D（`print 'n=' . count([1,2,3]);`）编译即 Signal 11（退出码 139）。
- A/B/C 对照组编译执行正常；修复后 test_unqlite/test_unqlite_ohos 全过（conan create 实测）。
- 归档：archives/u/unqlite/1.2.1/（notes.md / test_package/MANIFEST.yml / test_package/）。