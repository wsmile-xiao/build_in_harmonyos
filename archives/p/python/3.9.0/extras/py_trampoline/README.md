# _ctypes py_trampoline 备用方案

> **状态**: ⏸️ 备用（已验证可用，当前不启用）
> **创建日期**: 2026-03-28
> **最后验证**: 第 2 轮测试 63 ERROR → 46 ERROR + 1 FAIL（纯数值签名全通过）
> **适用版本**: Python 3.9.0
> **编译环境**: HarmonyOS aarch64, musl libc, Clang 15.0.4

## 背景

Python ctypes 的 `CFUNCTYPE` 回调需要 libffi 的 `ffi_closure_alloc()` 分配可执行内存。
鸿蒙内核 W^X 策略禁止 `mmap(PROT_EXEC)`，导致 `ffi_closure_alloc()` 返回 NULL → `MemoryError`。

**当前解决方案**: 另一个任务中已修复 libffi 使其兼容鸿蒙 W^X 策略，test_ctypes 全部通过。
**本方案为备用**: 如果 libffi 修复在某些场景下不可用，可切换到本方案。

## 方案原理

用预编译的 .so 代码段替代 libffi 的动态 closure：
- py_trampoline.c 编译进 _ctypes.so，所有 trampoline 代码在 .text 段（file-backed r-xp）
- 运行时通过 slot 管理 + 函数指针表分配 trampoline，零 mmap(PROT_EXEC)
- 对 Python 上层完全透明（CFUNCTYPE 无感知）

## 档案文件

| 文件 | 说明 |
|------|------|
| `py_trampoline_integration.c` | 编入 _ctypes.so 的 trampoline 实现（128 slots × 48 sigs） |
| `py_trampoline_v3.c` | 早期独立 .so 版本（16 slots × 14 sigs，Python 模块接口） |
| `py_trampoline_v3.so` | 早期独立 .so 编译产物 |
| `WORKPLAN.md` | 完整工作计划（签名分析、分层策略、风险） |
| `README.md` | py_trampoline_v3 使用说明 + 鸿蒙 mmap 限制验证 |
| `PROGRESS.md` | 实施进展（第 1 轮 + 第 2 轮结果） |

## 集成方法

### 需要修改的文件

1. **`Modules/_ctypes/py_trampoline.c`** — 复制本目录的 `py_trampoline_integration.c`
2. **`Modules/_ctypes/ctypes.h`** — 添加 `USE_PY_TRAMPOLINE` 守卫内的 extern 声明
3. **`Modules/_ctypes/callbacks.c`** — `#ifdef USE_PY_TRAMPOLINE` 替换 ffi_closure 路径
4. **`setup.py`** — OHOS 平台添加 py_trampoline.c + `-DUSE_PY_TRAMPOLINE`

### 开关

setup.py 中一行布尔值切换：
```python
USE_PY_TRAMPOLINE = True   # 启用 py_trampoline
USE_PY_TRAMPOLINE = False  # 回退到 libffi（默认）
```

## 签名覆盖（48 种）

| 类别 | 签名 | 示例 |
|------|------|------|
| int 返回 × 0-6 int 参数 | i_I0..i_I6 | `CFUNCTYPE(c_int, c_int, c_int)` |
| int 返回 × 1-6 double 参数 | i_D1..i_D6 | `CFUNCTYPE(c_int, c_double, c_double)` |
| int 返回 × 混合 | i_ID, i_DI | `CFUNCTYPE(c_int, c_byte, c_double)` |
| double 返回 × 0-6 int 参数 | d_I0..d_I6 | `CFUNCTYPE(c_double, c_int)` |
| double 返回 × 0-6 double 参数 | d_D0..d_D6 | `CFUNCTYPE(c_double, c_double)` |
| double 返回 × 混合 | d_ID, d_DI, d_IID | `CFUNCTYPE(c_double, c_byte, c_double)` |
| void 返回 × 0-6 int 参数 | v_I0..v_I6 | `CFUNCTYPE(None, c_int)` |
| void 返回 × 0-6 double 参数 | v_D0..v_D6 | `CFUNCTYPE(None, c_double)` |
| void 返回 × 混合 | v_ID, v_DI | `CFUNCTYPE(None, c_byte, c_double)` |

特殊处理：
- Pointer 类型 → 与 int64_t ABI 等价，自动复用 I 类签名
- struct >16 字节 → aarch64 隐藏指针，分类为 I
- long double / 小 struct by value → 不支持（罕见场景）

## 测试结果

### 第 1 轮（USE_PY_TRAMPOLINE=True）
- **之前**: 63 ERROR（全部 MemoryError）
- **之后**: 46 ERROR + 1 FAIL + 95 skipped
- 通过: test_byte/char/int/long/longlong/short/ubyte/uint/ulong/ulonglong/ushort, test_qsort, test_callbacks_with_pointers, test_callback_register_int, test_callback_register_double, test_pyobject, 所有 as_parameter 系列等

### 第 2 轮（增加混合签名 + 128 slots）— 未验证
预计可消除大部分剩余失败，仅剩 test_callback_too_many_args(1024参数) 和 test_unsupported_restype 等预期失败。

### libffi 修复路径（USE_PY_TRAMPOLINE=False，当前）
- **结果**: 0 ERROR, 0 FAIL, 95 skipped — 全部通过

## 风险

| 风险 | 说明 |
|------|------|
| 签名组合爆炸 | 当前 48 种覆盖 ~95% 场景，极端组合需额外添加 |
| struct by value <16 字节 | aarch64 在寄存器传递，trampoline 签名需精确匹配结构体布局 |
| slot 耗尽 | 128 slots + GC fallback，一般够用；极端场景可增到 256 |
| libffi 头文件依赖 | py_trampoline.c 仍 include ffi.h/ctypes.h，需 libffi 开发包 |
