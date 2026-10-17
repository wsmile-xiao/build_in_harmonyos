# DRAFT-cobs-c-0.4-py2-upstream-tests-py3-ctypes-cdll-port：Python2 ctypes 测试套件的 Python3.12 最小移植

> Contributor: pc4-9 | Status: Draft | Updated: 2026-09-20
> Source: cobs-c 0.4 适配（feat/cobs-c-0.4）；触发场景：UnitTestPython 6 个 py2 文件在 py3.12 收集即失败
> 对应：`knowledge/drafts/DRAFT-cobs-c-0.4-py2-upstream-tests-py3-ctypes-cdll-port.kv`

## 现象

上游 `UnitTestPython/` 测试文件头声明 "This version is for Python 2.x"。在 Python 3.12 下
pytest 收集直接报 4 errors：

```text
E   AttributeError: 'array.array' object has no attribute 'tostring'   # py3.9+ 移除
E   AttributeError: libcobs                                            # cdll 属性加载
E   name 'xrange' is not defined
```

且 wrapper 里 `ctypes.cdll.libcobs` 失败时抛 **AttributeError** 而非 py2 的 **OSError**，
`except OSError: LoadLibrary('./libcobs.so')` 兜底永不触发。

## 根因

1. **Python 2→3 API 移除**：`array.tostring`、`xrange`、`str` 字节语义、`.next()`、
   `print >> sys.stderr`。
2. **ctypes.cdll 属性式加载的异常语义变化**：py3.12 下 `ctypes.cdll.libcobs` 加载失败
   抛 AttributeError（属性查找失败），上游 wrapper 捕获 OSError 的兜底分支失效。
3. **dlopen 裸名搜索**：`ctypes.cdll.libcobs` 按 "libcobs"（无 .so 后缀）搜索，
   仅 LD_LIBRARY_PATH 含 `libcobs.so` 不会自动匹配，需要提供精确名符号链接
   `libcobs -> libcobs.so`（或显式 LoadLibrary 绝对路径）。

## 方案

**最小移植（仅语法/API 兼容，断言逻辑一字不改）**：
- `xrange(...)` → `range(...)`
- `array('B', ...).tostring()` → `.tobytes()`
- 字符串字面量 `"\x00"`/`"\xfe"` → 字节字面量 `b"\x00"`/`b"\xfe"`
- `non_zeros.next()` → `next(non_zeros)`
- `''.join(chr(i) for ...)` → `bytes(bytearray(...))`
- `print >> sys.stderr, X` → `print(X, file=sys.stderr)`

**运行时路径恢复（ctypes 动态库）**：
```bash
D=/storage/Users/currentUser/tmp/cobs-so-lib
ln -sf <build>/libcobs.so  $D/libcobs     # 精确名符号链接（关键！）
ln -sf <build>/libcobsr.so $D/libcobsr
LD_LIBRARY_PATH=$D python3 -m pytest test_cobs.py test_cobs_c.py test_cobsr.py test_cobsr_c.py -v
```

## 验证

- `22 collected, 22 passed, 0 failed`（8.54s）
- 覆盖：预定义编码/解码、解码错误、全 0 串（520 长度）、非 0 串（999）、随机数据 5000 轮闭环、
  NULL 指针、输出缓冲越界逐级检测（cobs 与 cobsr 两套）

## 适用边界 / 反例

- 适用：带 Python 2.x ctypes 绑定测试的 C 库在 py3.12 环境跑上游测试
- 反例：pybind11 绑定包（D.4-2 判 cpp，走 conan 主流程）；纯 Python 测试套件不走 ctypes 路径；
  动态库确实不适用/未被导出时保留 skip 并记录恢复条件

## 关系

- similar_to: E226（os.popen str/bytes py3.12）、E143（ctypes dlopen Permission denied）、
  E019（LD_LIBRARY_PATH/rpath）
- caused_by: Python 2→3 不兼容 | prerequisite_of: — | conflicts_with: —
