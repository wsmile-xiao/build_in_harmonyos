# _ctypes py_trampoline 集成工作计划

> **创建日期**: 2026-03-28
> **状态**: 🔄 规划完成，待实施
> **源码目录**: `~/python/Python-3.9.0-clean-v5`
> **知识库**: `$PROJECT_DIR`
> **关联 E045**: `knowledge/error-patterns.md` — mmap RWX 被拒（W^X 策略）

---

## 一、问题概述

### 1.1 症状

`test_ctypes` 63 个 ERROR，**全部是 `MemoryError`**，根因一致：

```
ERROR: test_byte (ctypes.test.test_callbacks.Callbacks)
...
CFUNCTYPE(c_int, c_byte)(callback_func)
MemoryError
```

任何 `CFUNCTYPE(...)(python_func)` 包装器创建都会失败。

### 1.2 根因链

```
CFUNCTYPE(func) 创建回调包装器
    ↓
callbacks.c:364  ffi_closure_alloc(sizeof(ffi_closure), &p->pcl_exec)
    ↓
Linux 路径: 调用 libffi 的 ffi_closure_alloc()
    ↓
libffi src/closures.c: mmap(PROT_READ|PROT_WRITE|PROT_EXEC)
    ↓
鸿蒙内核 W^X 策略: EINVAL (errno 22)
    ↓
返回 NULL → PyErr_NoMemory() → MemoryError
```

### 1.3 已确认的事实

| 事实 | 来源 |
|------|------|
| libffi ffi_closure_alloc() 在鸿蒙返回 NULL | libffi 3.5.2 manifest.yaml |
| 鸿蒙内核完全禁止创建可执行内存页 | test_mmap.c 验证（见 README.md） |
| 普通 ctypes 函数调用（无回调）正常 | `CDLL(None).abs(-42) == 42` ✅ |
| `CFUNCTYPE` 类型创建本身 OK，包装器创建失败 | 验证通过 |
| libffi 方案不可行 | 其他对话已确认 |

---

## 二、解决方案：py_trampoline 替代 ffi_closure

### 2.1 核心思路

**不使用 libffi 的动态 closure，改用预编译的 .so 代码段作为跳板。**

- `py_trampoline.so` 的代码段是 file-backed `r-xp`，鸿蒙允许
- 所有回调跳板代码编译时已确定，运行时零 mmap
- 对 Python 上层完全透明（CFUNCTYPE 无感知）

### 2.2 当前 py_trampoline_v3.c 状态

| 项 | 状态 |
|-----|------|
| 基础框架 | ✅ 16 slots × 14 signatures = 224 个预编译函数 |
| 纯 C 实现 | ✅ 零 inline asm，零 mmap(PROT_EXEC) |
| GIL 安全 | ✅ PyGILState_Ensure/Release |
| Python 模块接口 | ✅ alloc_slot / register / get_trampoline_ptr |
| 基础验证 | ✅ 4 个签名通过（ii, dd, vi, iii） |
| .so 文件 | ✅ 已编译 |

### 2.3 签名覆盖分析（当前 vs 需求）

#### 当前 v3 支持的 14 种签名

| sig | C 签名 | ctypes 对应 |
|-----|--------|-------------|
| `i0` | `int64_t()` | `CFUNCTYPE(c_int)` |
| `ii` | `int64_t(int64_t)` | `CFUNCTYPE(c_int, c_int)` |
| `id` | `int64_t(double)` | `CFUNCTYPE(c_int, c_double)` |
| `iii` | `int64_t(int64_t, int64_t)` | `CFUNCTYPE(c_int, c_int, c_int)` |
| `iiiii` | `int64_t(×5)` | `CFUNCTYPE(c_int, c_int, c_int, c_int, c_int)` |
| `idddd` | `int64_t(double×5)` | `CFUNCTYPE(c_int, c_double, c_double, c_double, c_double, c_double)` |
| `dd` | `double(double)` | `CFUNCTYPE(c_double, c_double)` |
| `di` | `double(int64_t)` | `CFUNCTYPE(c_double, c_int)` |
| `ddddd` | `double(double×5)` | `CFUNCTYPE(c_double, c_double, c_double, c_double, c_double)` |
| `diiii` | `double(int64_t×5)` | `CFUNCTYPE(c_double, c_int, c_int, c_int, c_int, c_int)` |
| `vi` | `void(int64_t)` | `CFUNCTYPE(None, c_int)` |
| `vd` | `void(double)` | `CFUNCTYPE(None, c_double)` |
| `vii` | `void(int64_t, int64_t)` | `CFUNCTYPE(None, c_int, c_int)` |
| `v0` | `void()` | `CFUNCTYPE(None)` |

#### test_ctypes 实际需要的签名（按优先级）

**P0 — 无 pointer 参数，v3 已覆盖或需少量扩展：**

| 需求签名 | 对应测试 | v3 状态 |
|----------|----------|---------|
| `i0` | `CFUNCTYPE(c_int)` | ✅ 已有 |
| `ii` | `CFUNCTYPE(c_int, c_int)` | ✅ 已有 |
| `di` | `CFUNCTYPE(c_double, c_int)` | ✅ 已有 |
| `dd` | `CFUNCTYPE(c_double, c_double)` | ✅ 已有 |
| `vi` | `CFUNCTYPE(None, c_int)` | ✅ 已有 |
| `vd` | `CFUNCTYPE(None, c_double)` | ✅ 已有 |
| `v0` | `CFUNCTYPE(None)` | ✅ 已有 |
| `iii` | `CFUNCTYPE(c_int, c_int, c_int)` | ✅ 已有 |
| `iiiii` | `CFUNCTYPE(c_int, ×5)` | ✅ 已有 |
| `idddd` | `CFUNCTYPE(c_int, double×5)` | ✅ 已有 |
| `ddddd` | `CFUNCTYPE(c_double, double×5)` | ✅ 已有 |
| `vii` | `CFUNCTYPE(None, c_int, c_int)` | ✅ 已有 |
| `viii` | `CFUNCTYPE(None, c_int, c_int, c_int)` | ❌ **缺少** |
| `iiiii` (6 args) | `CFUNCTYPE(c_int, c_int, c_int, c_int, c_int, c_int)` | ❌ **需 6 参数变体** |

**P1 — 需要 pointer 参数变体：**

| 需求签名 | 对应测试 | v3 状态 |
|----------|----------|---------|
| `i_pp` | `CFUNCTYPE(c_int, POINTER(c_int), POINTER(c_int))` — qsort | ❌ **缺少** |
| `i_pp_char` | `CFUNCTYPE(c_int, POINTER(c_char), POINTER(c_char))` — _ctypes_test qsort | ❌ **缺少** |
| `i_p` | `CFUNCTYPE(c_int, POINTER(c_int))` — test_pointers | ❌ **缺少** |
| `v_p` | `CFUNCTYPE(None, c_void_p)` — 部分 callback | ❌ **缺少** |
| `i_pp_large` | `CFUNCTYPE(c_int, POINTER(large_struct), ...)` | ❌ **缺少** |

**P2 — 特殊类型：**

| 需求 | 对应测试 | 说明 |
|------|----------|------|
| `c_longdouble` | test_longdouble | long double 返回/参数 |
| `c_char_p` 字符串 | 部分 callback | `const char*` ↔ Python bytes |
| `py_object` | test_pyobject | `PyObject*` ↔ Python object |

### 2.4 关键设计问题

#### Q1: pointer 参数如何传递？

**核心难点**：`CFUNCTYPE(c_int, POINTER(c_int), POINTER(c_int))` 中，pointer 是 `void*`（8 字节整数），在 C ABI 层面和 `int64_t` 完全等价。所以：

```c
// pointer 参数在 C ABI 中就是 int64_t
int64_t tr_s0_i_pp(int64_t p1, int64_t p2) {
    return _call_i2(0, p1, p2);  // 复用 _call_i2
}
```

**Python 侧需要将 pointer 转为整数传给 Python 回调，再转回 pointer**。

#### Q2: 集成点在哪里？

**方案确定（README.md 已确认）：C 层修改 `Modules/_ctypes/malloc_closure.c`**

```
callbacks.c:364
    p->pcl_write = ffi_closure_alloc(sizeof(ffi_closure), &p->pcl_exec);
    
    #ifdef __OHOS__
    // 替换为 py_trampoline slot 分配
    p->pcl_write = py_trampoline_alloc(...);
    p->pcl_exec = py_trampoline_get_exec_ptr(...);
    #endif
```

#### Q3: Python 可调用对象如何桥接到 C？

py_trampoline 的 `_call_i1` 等函数通过 `PyObject_CallFunction` 调用 Python 对象。
在 C 层集成时，需要将 `CThunkObject->callable` 注册到对应 slot。

---

## 三、实施计划

### Phase 1: 扩展 py_trampoline_v3.c 签名覆盖 ⏳

**目标**：覆盖 test_ctypes 中所有非 pointer 的 callback 签名

| 步骤 | 任务 | 说明 |
|------|------|------|
| 1.1 | 增加 `viii` (void, int×3) 签名 | test_structures 需要 |
| 1.2 | 增加 6 参数变体 `iiiiii`, `viiii` | test_callback_register_int 需要 |
| 1.3 | 增加更多中间参数数量变体 (3,4 参数) | 部分测试需要 |
| 1.4 | 编译验证新增签名 | .so 编译 + 基础测试 |
| 1.5 | 增加 pointer 参数变体 `i_pp`, `i_pp_char`, `i_p`, `v_p` | qsort, test_pointers 需要 |
| 1.6 | pointer→PyObject 转换 | `_call_i2` 中将 int64_t 转为 ctypes 指针对象 |

**签名扩展策略**：

由于 test_ctypes 涉及的签名组合非常多（不同参数数量 × 不同类型 × pointer 变体），
穷举法不现实。建议采用以下分层策略：

- **Layer 1**: 纯数值型（最多 6 参数），覆盖 80% 的测试
- **Layer 2**: pointer 参数（1-2 个 pointer），覆盖 qsort 等剩余测试
- **Layer 3**: 特殊类型（longdouble, pyobject），可后续迭代

### Phase 2: C 层集成（修改 _ctypes 源码） ⏳

**目标**：修改 CPython _ctypes 模块，使其在 `__OHOS__` 下使用 py_trampoline

| 步骤 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 2.1 | 添加 py_trampoline.c 到 _ctypes 构建源 | `setup.py` 或 `Makefile.pre.in` | 编入 _ctypes.so |
| 2.2 | 修改 malloc_closure.c | `Modules/_ctypes/malloc_closure.c` | `#ifdef __OHOS__` 分支 |
| 2.3 | 修改 callbacks.c | `Modules/_ctypes/callbacks.c` | 注册 callable 到 slot，获取函数指针 |
| 2.4 | 处理签名匹配逻辑 | 新增或修改 | 将 ffi_type 序列映射到 py_trampoline sig |
| 2.5 | 处理 ffi_prep_closure_loc 替代 | `Modules/_ctypes/callbacks.c` | 跳过 libffi closure 准备 |
| 2.6 | 编译验证 | - | make + 扩展模块验证 |

### Phase 3: test_ctypes 验证 ⏳

**目标**：63 个 ERROR 全部消除

| 步骤 | 任务 | 说明 |
|------|------|------|
| 3.1 | 跑 test_ctypes 获取新基线 | 确认哪些通过/失败 |
| 3.2 | 分析剩余失败 | 是否签名未覆盖或 pointer 转换问题 |
| 3.3 | 迭代修复 | 扩展签名或修复转换逻辑 |
| 3.4 | 全量 489 测试通过确认 | 目标 0 ERROR |

### Phase 4: 归档与知识沉淀 ⏳

| 步骤 | 任务 |
|------|------|
| 4.1 | 更新 manifest.yaml（3.9.0） |
| 4.2 | 更新 E045 error-patterns.md 添加解决方案 |
| 4.3 | 更新 knowledge/python-extensions.md _ctypes 章节 |
| 4.4 | gen_summary.py 更新 SUMMARY.md |

---

## 四、风险与注意事项

| 风险 | 等级 | 应对 |
|------|------|------|
| 签名组合爆炸 | 🟡 中 | 分层覆盖，Pointer 统一为 int64_t 传递 |
| ffi_prep_closure_loc 被跳过后 ABI 兼容 | 🟡 中 | aarch64 AAPCS64 下函数指针就是代码地址，跳板函数指针与 closure 指针布局需一致 |
| 线程安全 | 🟢 低 | 每个 slot 独立，GIL 保护 |
| slot 耗尽（16 个不够） | 🟡 中 | 可扩展到 64 或实现 slot 回收 |
| struct by value callback 参数 | 🔴 高 | 较少见但 test_callback_large_struct 可能涉及 |

---

## 五、test_ctypes 63 个 ERROR 分布

```
test_callbacks.Callbacks (16 errors)
  ├── test_byte, test_char, test_double, test_float, test_int, test_long
  ├── test_longdouble, test_longlong, test_pyobject, test_short
  ├── test_ubyte, test_uint, test_ulong, test_ulonglong, test_ushort
  ├── test_unsupported_restype_1, test_unsupported_restype_2
  ├── test_issue12483, test_issue_7959

test_callbacks.SampleCallbacksTestCase (5 errors)
  ├── test_callback_large_struct
  ├── test_callback_register_double
  ├── test_callback_register_int
  ├── test_callback_too_many_args
  ├── test_convert_result_error
  └── test_integrate

test_as_parameter (12 errors)
  ├── test_callbacks, test_callbacks_2, test_longlong_callbacks, test_shorts
  └── × 3 个 TestCase 类

test_functions (5 errors)
  ├── test_callbacks, test_callbacks_2, test_longlong_callbacks
  ├── test_sf1651235, test_shorts

test_pointers (1 error)
  └── test_callbacks_with_pointers  ← 需要 pointer 参数变体

test_libc (1 error)
  └── test_qsort  ← 需要 CFUNCTYPE(c_int, POINTER(c_char), POINTER(c_char))

test_funcptr (3 errors)
  ├── test_basic, test_first, test_structures

test_pickling (6 errors)
  └── test_unpickable × 6

test_prototypes (1 error)
  └── test (ArrayTest)

test_random_things (4 errors)
  └── test_FloatDivisionError, test_IntegerDivisionError
      test_TypeErrorDivisionError, test_ValueError

test_refcounts (3 errors)
  └── test_callback, test_1, test_refcount

test_simplesubclasses (2 errors)
  └── test_ignore_retval, test_int_callback
```

---

## 六、test_ctypes 非 callback 类的 95 个 skipped

这 95 个跳过不是本次任务范围，主要是：
- Windows 专用测试 (WINFUNCTYPE)
- 结构体大小/对齐差异
- 部分平台限制

---

*创建者: OpenDesk*
*基于 py_trampoline_v3 方案（其他对话已确认 libffi 不可行）*
