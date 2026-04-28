# _ctypes py_trampoline 集成 — 进展存档

> **日期**: 2026-03-28
> **状态**: 🔧 代码修改完成，待编译验证（第 2 轮）

## 第一轮结果 (63 ERROR → 46 ERROR + 1 FAIL)

### 修改的文件
| 文件 | 操作 |
|------|------|
| `Modules/_ctypes/py_trampoline.c` | 新建 — 128 slots × 48 sigs |
| `Modules/_ctypes/ctypes.h` | 添加 _CallPythonObject extern + py_trampoline API |
| `Modules/_ctypes/callbacks.c` | #ifdef __OHOS__ 替换 ffi_closure |
| `setup.py` | OHOS 添加 py_trampoline.c + -D__OHOS__ |

### 第 1 轮通过
- test_byte/char/int/long/longlong/short/ubyte/uint/ulong/ulonglong/ushort — 纯整数 ✅
- test_qsort, test_callbacks_with_pointers — pointer 参数 ✅
- CFUNCTYPE(c_double, c_double) — 纯 double 签名 ✅
- test_callback_register_int (6 args) ✅

### 第 1 轮失败分析 & 第 2 轮修复

**A: 混合类型 d(i,d)** — test_double/float 等 check_type 第 2 行
→ 添加 ID/DI/IID 混合 trampolines ✅

**B: Slot 耗尽 MemoryError** — 32 slots 不够
→ MAX_SLOTS=128 + PyGC_Collect fallback ✅

**C: struct by value** — test_callback_large_struct, 24 字节 > 16 字节 aarch64 隐藏指针
→ _classify_type: FFI_TYPE_STRUCT size>16 → 'I' ✅

**D: refcount 泄漏** — test_issue_7959
→ 待分析

**E: 预期不可用** — test_callback_too_many_args(1024 args), test_unsupported_restype

## 编译命令
```bash
cd ~/python/Python-3.9.0-clean-v5
make clean && make
LD_LIBRARY_PATH=.:~/usr/local/lib ./python3.9 -m test test_ctypes -v 2>&1 | tee ~/tmp/test_ctypes_r2.log
grep -E "^(ERROR|FAIL)" ~/tmp/test_ctypes_r2.log
```
