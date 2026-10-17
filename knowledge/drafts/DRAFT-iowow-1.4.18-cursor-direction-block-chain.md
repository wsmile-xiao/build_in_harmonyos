# DRAFT-iowow-1.4.18-cursor-direction-block-chain

## 问题

对 iowow 1.4.18 写消费者游标有序遍历断言（沿 1.5.x 经验：BEFORE_FIRST + IW_CURSOR_NEXT 取最小键起步），test_package 报：

```console
FAIL: cursor starts at smallest key (sorted order)
```

实测 `iwkv_cursor_open(db, &cur, IWKV_CURSOR_BEFORE_FIRST)` 后第一条
`iwkv_cursor_to_next(cur, &k, &v)` 返回的是**最大**键（key-4），遍历顺序
为 key-4 → key-3 → key-2 → key-1（降序）。

## 根因

1.4.x 块链实现的游标初始化方向（src/kv/iwkv.c:2763 `_cursor_to_lr`）：

- `IWKV_CURSOR_BEFORE_FIRST` → 从索引尾部（KVBLK_IDXNUM-1，高地址）起，
  NEXT 沿块链向键**递减**方向移动；
- `IWKV_CURSOR_AFTER_LAST` → dbaddr=-1 从链头起，PREV 向键**递增**方向移动。

上游 `src/kv/tests/iwkv_test1.c` L490-539 的期望正是这个语义
（BEFORE_FIRST+NEXT 首条断言为最大键）。1.5.x 重写游标后方向相反。
这是**版本行为差异**，不是 bug——两边各自的上游测试都按各自语义 PASS。

## 解决

写升序遍历用 **AFTER_LAST + PREV**：

```c
iwkv_cursor_open(db, &cur, IWKV_CURSOR_AFTER_LAST);
while (iwkv_cursor_to_prev(cur, &k, &v) == 0) {
  /* 键升序：key-1 → key-2 → ... */
  iwkv_kv_dispose(db, &k, &v);   /* 游标数据必须释放 */
}
```

不修改库源码；测试断言按 1.4.x 语义写。

## 边界（适用条件与禁止）

- 适用：iowow 1.4.x（块链游标）的消费者；从 1.5.x 迁移到 1.4.x 的代码
  须反转游标方向假设。
- 不适用：iowow 1.5.x（方向已反）；非游标 API（iwkv_get/put/del 无差异）。
- 禁止：因断言失败就断定库有 bug 而去改上游源码——先对照
  iwkv_test1.c 的上游期望确认版本语义。
- 游标返回的 k/v 是堆分配，必须 `iwkv_kv_dispose()` 释放，否则 WAL/文件锁
  关闭阶段可能挂起。

## 验证

- test_package 30/30 PASS（游标段 AFTER_LAST+PREV 升序断言）；
- 独立调试程序两次复现方向差异（dbg_cursor.c：BEFORE_FIRST+NEXT 得
  key-4→key-1 降序，AFTER_LAST+PREV 得 key-1→key-4 升序）；
- 上游 23 执行器全 PASS 佐证库行为与上游测试期望一致。
