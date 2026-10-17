# Draft: OHOS 静态 glib 双实例 GObject 类型系统冲突 — 消费者 unref 库内 GObject 崩溃

- **Draft ID**: DRAFT-libxmlb-static-glib-double-instance
- **来源软件**: libxmlb 0.3.19
- **发生阶段**: 消费者/test_package 运行时（unref/类型检查）
- **状态**: 待人工审核提升为正式 E 条目

## 错误特征

```
(unknown terminal GC) Signal 11 (core dumped)   # g_object_unref(silo) 时
XbSilo-CRITICAL **: xb_builder_source_load_file: assertion 'G_IS_FILE(file)' failed
```

probe 二分证据：
- `g_ptr_array_unref(results)` → OK
- `g_object_unref(silo)` → Signal 11（SIGSEGV）
- 不清理、直接退出 → exit 0

## 根因

本仓库 glib/2.88.0 制品为**静态库**（options: shared=False）。libxmlb.so 链接期将 glib/gio
静态嵌入自身（`nm -D libxmlb.so.2.0.0 | grep " U g_"` 为空，NEEDED 仅 libzstd.so.1/libc.so）。
消费者 test 二进制另行静态链接同一 glib，进程内出现**两份独立 GObject 类型系统**：
库内创建的对象，其类型 ID 是 libxmlb 嵌入副本的；消费者侧 `G_IS_FILE`/`g_object_unref`
按消费者副本的类型注册表比对，跨边界时类型检查失败或释放路径错乱 → SIGSEGV。
（GFile 由消费者 gio 创建、经 libxmlb 嵌入 gio 校验 → G_IS_FILE 失败，同源。）

## 修复

消费者测试/鸿蒙专项测试的清理段**不 unref 库内 GObject/GPtrArray**，由进程退出回收；
仅释放测试自身分配（g_free 返回字符串、g_error_free）。上游自测 xb-self-test 在单进程内
自包含（库内创建、库内释放），不受影响。

## 验证

- 鸿蒙专项测试与 test_package 运行 PASSED（exit=0）
- probe3（不清理）exit=0 vs probe2（unref silo）SIGSEGV
- `nm -D libxmlb.so.2.0.0 | grep -c " U g_"` = 0（glib 静态嵌入证实）

## 适用边界 / 反例

- 适用：OHOS 上任何静态 glib（shared=False）环境交付 .so 的库，其消费者与 test_package
- 反例：glib 提供 shared 制品后（依赖以动态库参与链接），类型系统单一，跨库 unref 恢复安全；
  上游自测单进程场景无此问题

## 查重差异（vs E444 / E123）

- E444：.init_array 构造器未运行导致类型系统未初始化 → 显式 `g_type_ensure_initialized()`；
  根因是初始化时机，本候选根因是双实例类型系统，机制与修复不同
- E123：meson 静态 libintl 链接 undefined symbol（链接期符号缺失）；本候选是运行期类型系统冲突。
  均无覆盖，属新增候选，可跨库复用（影响所有静态 glib 消费者的测试编写）