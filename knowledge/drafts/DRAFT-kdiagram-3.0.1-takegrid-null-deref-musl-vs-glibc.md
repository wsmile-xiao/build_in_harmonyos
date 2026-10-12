# DRAFT: kdiagram 3.0.1 — takeGrid() 空指针成员访问（glibc 良性 UB vs OHOS musl/clang SIGSEGV）

> 草稿状态：pending-editor-review（编号由主编确认）
> 载体：PR #14653（archives/k/kdiagram/3.0.1，patch 内含回移植 hunk）
> 类别：platform | portability | musl-vs-glibc | null-deref | upstream-fix-backport

## 错误特征（error_signature）

```
Received signal 11 (SIGSEGV), code SEGV_MAPERR, ... accessing address 0x0000000000000004
4/23 Test #4: KGanttView ...***Exception: SegFault
TestKGanttView::testSetGraphicsView ... SIGSEGV
```

崩溃点固定：`TestKGanttView::testSetGraphicsView`，访问地址恒为 `0x4`（nullptr this + 成员偏移的典型形态）。

## 根因（root_cause）

kdiagram ≤3.0.1 的 `KGantt::GraphicsScene::takeGrid()`（src/KGantt/kganttgraphicsscene.cpp）在函数入口**无条件**执行：

```cpp
AbstractGrid *GraphicsScene::takeGrid()
{
    AbstractGrid *grid = d->grid;
    grid->disconnect( this );   // ← d->grid 可能为 nullptr
    ...
}
```

`d->grid` 在 `KGantt::View` 构造后未调用 `setGrid` 时为 nullptr。上游测试
`TestKGanttView::testSetGraphicsView` 恰好用全新 View（从未 setGrid）调
`setGraphicsView(gv)` → 内部 `takeGrid()` → 空指针成员访问。

**平台可见性差异（本条目的核心价值）**：
- glibc/GNU 工具链：该 UB 良性（虚表解析碰巧不崩或被宽松内存布局掩盖）→ 上游 KDE CI 全绿，3.0.1 官方发布带病
- OHOS musl loader + clang 15（aarch64）：必崩 SIGSEGV@0x4
- 同一份测试代码两个平台呈现相反结论——"上游 CI 绿 ≠ OHOS 绿"的实证样本

**官方修复实锤**：上游 v3.0.1 之后的 commit 15a4437（"Fix more leaks"，2026-09-02，
Carl Schwan）为 `takeGrid()` 补了 `if (grid)` 守卫——证明这是真实 bug 而非 OHOS 独有，
只是 glibc 上从未暴露。

## 修复方案（solution）

① 整 hunk 回移植上游守卫（PR #14653 patches/0001-ohos-drop-printsupport.patch 内，
patch 注释注明上游 commit）：

```cpp
AbstractGrid *GraphicsScene::takeGrid()
{
    AbstractGrid *grid = d->grid;
    if (grid) {                       // upstream 15a4437 backport
        grid->disconnect( this );
    }
    d->grid = nullptr;
    if (grid) {
        connect( &d->default_grid, SIGNAL(gridChanged()), this, SLOT(slotGridChanged()) );
    }
    return grid;
}
```

② **通用定位范式**（OHOS 独有崩溃 + 上游 CI 绿时优先走这条，不要自行发明修法）：

```bash
git clone --depth 300 https://invent.kde.org/<group>/<repo>.git
git log v<version>..HEAD --oneline -- <崩溃源文件>
# 出现 fix/crash/leak/asan 字样的 commit = 官方修复，整 hunk 回移植并注明 hash
```

## 降级方案（fallback）

上游无对应修复（真·平台差异）时：对空指针成员访问逐点补守卫，保持函数签名与返回值
语义不变。**测试侧不可用 QEXPECT_FAIL 掩盖段错误**——SIGSEGV 无法被 QVERIFY 捕获，
必须在库代码层修复。

## 验证（verify_builds）

- PR #14653 本地 conan create 实证：修复前 ctest 22/23（KGanttView SIGSEGV）→
  回移植后 **23/23 passed (100%)**（日志：`100% tests passed, 0 tests failed out of 23`）
- 隔离复现：`KGanttView testSetGraphicsView` 单函数必崩、`testApi` 单函数通过
  （崩溃与打印裁剪无关——发生在纯 model/view 交换路径）

## 参考（reference_impl）

- 上游官方修复：https://invent.kde.org/graphics/kdiagram/-/commit/15a4437
- 同 PR 关联场景：qtbase/6.11.1 线 PrintSupport=OFF 下，KDE 模块优先用上游原生
  QT_NO_PRINTER/HAVE_PRINTER 宏守卫降级（kdiagram 模式零手写 no-op；对照
  kgraphviewer 26.04.0 手写 13 对 no-op 源文件的重路径）——两个场景共同构成
  "上游原生降级路径优先于手写补丁"的方法论。
