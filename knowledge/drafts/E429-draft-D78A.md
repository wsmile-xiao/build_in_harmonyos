# E429 — 对 GBoxed 调用 g_object_unref 导致 SIGSEGV

## 错误特征
libgobject-2.0.so.0 内 `g_object_run_dispose` SIGSEGV，fault 地址 @0x1（NULL+1），
x8 寄存器 = 1。崩溃栈全部位于 gobject 内部（g_object_run_dispose → 弱引用
datarlist 清理），极易误判为"gobject 库损坏"或"平台问题"。

## 触发条件
- 构建系统: meson（任意——运行时崩溃，与构建系统无关）
- 阶段: test/run（test_package 探针或下游消费者程序）

## 根因分析
对象实际是 GBoxed（`G_DEFINE_BOXED_TYPE` 注册，内存布局 = gatomicrefcount +
数据字段），消费者代码却用 `g_object_unref()` 释放。GObject 内部把 boxed
内存当 GObject 结构解释：数据字段（如 AdwSpringParams.mass，offset 16）的
double 位模式被当弱引用 datalist 指针解引用 → NULL 族地址 → SIGSEGV。
对照组实证：真 GObject（G_TYPE_OBJECT、自定义类型）创建+unref 全部正常，
库与平台均无问题，根因在测试侧 API 误用。

## 解决方案

### 推荐方案
释放前查头文件类型宏：`G_DEFINE_BOXED_TYPE` → 用 boxed 专用 unref
（如 `adw_spring_params_unref`）；`G_DEFINE_TYPE` → 用 `g_object_unref`。

### 禁止做法
- ❌ SIGSEGV 落在 g_object_run_dispose 时直接假设 gobject 库损坏（先用最小
  GObject 对照组分离"平台/库问题"vs"对象类型误用"）
- ❌ 对 GBoxed 调用 g_object_unref / g_object_ref

## 验证
```bash
# 最小对照组：同进程内 真 GObject 创建+unref（应正常）
# vs 对 GBoxed 调 g_object_unref（应 SIGSEGV @ g_object_run_dispose）
# 两者对比即可确认类型混淆
```

## 关联条目
- 相关: E471（display 测试分类与无显示 API 探针）
