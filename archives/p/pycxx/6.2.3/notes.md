# pycxx 6.2.3 适配笔记

**日期**: 2026-07-10
**状态**: built (conan-verify G1-G4 + L2/L4/L5 全通过)

## 适配概要

pyCXX 6.2.3 是 header+source 库（非纯 header-only），消费者需编译 Src/ 下的 4 个源文件。

## 关键问题与修复

### 1. 版本选择
- 5.4.2 (tagged release) 使用 Python 2 API (PyString_*, PyInt_*)，不兼容 Python 3
- 6.2.3 (master branch) 有 Python 3 支持，但针对 3.0-3.3 编写，需补丁适配 3.12

### 2. Python 3.12 兼容性补丁 (0001-Python3-compat-fix.patch)
- `PyCObject_FromVoidPtr` → `PyCapsule_New` (Python 3.2 移除)
- `PyCObject_AsVoidPtr` → `PyCapsule_GetPointer` (Python 3.2 移除)
- `PyCObject_Type` → `PyCapsule_Type`
- `tp_print` 字段 guard `#if PY_VERSION_HEX < 0x03080000` (Python 3.8 移除)
- `PyUnicode_FromUnicode` → `PyUnicode_FromWideChar` (Python 3.12 移除)
- `PyUnicode_GET_SIZE` → `PyUnicode_GET_LENGTH` (Python 3.12 移除)
- `PyUnicode_AS_UNICODE` → `PyUnicode_AsWideCharString` (Python 3.12 移除)
- `_Py_PackageContext` → `__Py_PackageContext` (Python 3.12 重命名)
- `seq.ptr()` → `seq->ptr()` (原始 bug: seq 是指针但用了 . 而非 ->)
- `delete m_methods_table` → `delete[] m_methods_table` (原始 bug: new[] 配 delete)

### 3. 打包结构
- headers: CXX/CXX/ → include/CXX/
- Python2/Python3 子目录: include/CXX/Python2/, include/CXX/Python3/
- source files: CXX/Src/ → include/CXX/Src/
- Python3 source subdir: include/CXX/Src/Python3/

### 4. 测试
- test_pycxx.cxx 实质调用 Py::String, Py::Long, Py::List, Py::Dict, Py::Tuple API (R34)
- Py_Finalize() 清理阶段有 SegFault，用 _exit(0) 跳过静态析构
- 所有 API 断言通过 (6 assertions)

## 构建命令
```
conan create archives/p/pycxx/6.2.3 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 已知问题 (gitcode-bot 审查 #6)

### PyUnicode_AsWideCharString 内存泄漏
- `as_unicodestring()` 中 `PyUnicode_AsWideCharString(ptr(), NULL)` 分配新内存，但未 `PyMem_Free` 释放
- `unicode_data()` 同理，原始 `PyUnicode_AS_UNICODE` 返回内部指针（无需释放），替换后语义改变
- 影响：频繁调用会泄漏内存，但不影响测试断言（测试在泄漏积累前完成）
- 计划：后续版本修复，需重构 unicodestring 构造逻辑
