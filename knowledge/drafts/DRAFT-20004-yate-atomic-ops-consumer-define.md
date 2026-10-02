# DRAFT-20004: yate 公共头要求消费者定义 ATOMIC_OPS（否则 incomplete type RLock）

- 条目主题：yate 公共头（yateclass.h）的 `YATOMIC_OP_LOCK_*` 宏受 `ATOMIC_OPS` 门控——消费者编译未定义该宏时，宏展开为 `RLock lck(m_lock)`，而公共头只有 `RLock` 前向声明，任何包含 `yatephone.h` 的消费者 TU 必现 `incomplete type` 硬错误；修复 = `cpp_info.defines = ["ATOMIC_OPS"]`（对齐上游 `yate-config --cflags` 契约）。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：yate 6.4.1；同范式适用于"公共头宏分支依赖 configure 探测结果"的包。

## 错误特征
- `yateclass.h:1270:6: error: variable has incomplete type 'TelEngine::RLock'`
- 展开行：`YATOMIC_OP_LOCK_READ` → `#define YATOMIC_OP_LOCK_READ RLock lck(m_lock)`
- 库自身编译全部正常（in-tree 编译行均带 `-DATOMIC_OPS`）——错误只出现在**消费者**侧

## 根因
1. yateclass.h L1150 区域：`#ifdef ATOMIC_OPS`（且非 `_WINDOWS`）→ `YATOMIC_OP_LOCK_READ` = `{}`；否则 = `RLock lck(m_lock)`。
2. 公共头只有 `class RLock;` 前向声明（完整定义在非公共头）；非模板 inline 方法体必须完整类型。
3. 上游消费者契约经 `yate-config --cflags` 传递（含 `-DATOMIC_OPS`）——Conan 消费者不自动获得，需 `cpp_info.defines` 显式重传。

## 修复
```python
def package_info(self):
    self.cpp_info.defines = ["ATOMIC_OPS"]   # CMakeDeps → 消费者 -DATOMIC_OPS
```
勿传播 `HAVE_BLOCK_RETURN`（`YSTRING` 语句表达式分支两态均可编译）与 `HAVE_GCC_FORMAT_CHECK`（警告级属性）。

## 通用化判据
上游公共头的宏分支依赖 configure 探测结果时：
1. 先跑上游元数据工具（`<pkg>-config --cflags` / `pkg-config --cflags`）取得完整探测宏集；
2. 逐一判断哪些宏影响公共头的**可编译性**（硬错误）vs 仅性能/警告——只重传前者；
3. 用 `cpp_info.defines` 重传，注释注明与上游 `--cflags` 的对齐关系。

## 验证
- yate 6.4.1：消费者 test.cpp 不传 `ATOMIC_OPS` 必现 incomplete type（2026-09-30 实测）；`defines=["ATOMIC_OPS"]` 后 test_package 5/5 断言通过。
