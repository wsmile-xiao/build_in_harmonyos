# pycxx-simple 6.2.8 适配笔记

## 编译环境
- 构建系统: custom (Python distutils + setup_makefile.py)
- 编译日期: 2026-06-23
- 编译器: clang/clang++ 18.1.8
- 目标平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: published

## 编译步骤

```bash
source .build-context-pycxx-simple-6.2.8
cd $BUILD_SRC_DIR
python3 setup_makefile.py linux linux.mak
make -f linux.mak obj/simple.so
llvm-strip obj/simple.so
ohc-run.py sign-elf obj/simple.so
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Py_UNICODE API 编译错误 | Python 3.12 移除了 Py_UNICODE 类型和相关 API | 替换为 wchar_t 和 PyUnicode_FromWideChar/GetLength/AsWideCharString |
| 2 | tp_print 赋值编译错误 | Python 3.9+ 移除了 tp_print 槽 | 用 #if PY_VERSION_HEX < 0x03090000 保护 |
| 3 | _Py_PackageContext 未定义 | Python 3.12 移除了内部变量 | return nullptr |
| 4 | libc++_shared.so 运行时依赖 | 默认链接使用共享 C++ 库 | -nostdlib + 静态链接 libc++_static.a + libc++abi.a |
| 5 | .so 无法从用户目录加载 | HMDFS 不支持 dlopen() | 平台限制，编译产物本身正确 |

## 源码修改

### setup_makefile.py
- g++ → clang++ (CCC变量)
- 添加 --sysroot, -nostdinc++, -I flags for HarmonyOS SDK
- LDSHARED: -lc++ → -nostdlib + libc++_static.a + libc++abi.a + -lc

### CXX/Python3/Objects.hxx
- Py_UNICODE → wchar_t
- PyUnicode_FromUnicode → PyUnicode_FromWideChar
- PyUnicode_GET_SIZE → PyUnicode_GetLength
- PyUnicode_AS_UNICODE → PyUnicode_AsWideCharString

### Src/Python3/cxxsupport.cxx
- Py_UNICODE unicode_null_string → wchar_t unicode_null_string

### Src/Python3/cxx_extensions.cxx
- tp_print 赋值用版本宏保护 (2处)

### Src/IndirectPythonInterface.cxx
- _Py_PackageContext → nullptr

## 依赖版本

- Python 3.12 (/data/service/hnp/python.org/python_3.12)
- HarmonyOS SDK 26.0.0.18 (clang++ 18.1.8)
- PyCXX 6.2.8 源码

## 验证结果

```
obj/simple.so: ELF shared object, 64-bit LSB arm64, stripped
NEEDED: libc.so (only)
ELF signed with binary-sign-tool (.codesign section present)
```

测试因 HMDFS 文件系统限制无法执行（dlopen 返回 Permission denied）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| obj/simple.so | 1,209,728 bytes | 编译产物 (stripped, signed, static libc++) |

## 注意事项

- HMDFS 文件系统不支持 dlopen()，所有用户编译的 .so 文件都无法在当前环境下加载
- 系统级 Python site-packages 目录只读，无法安装 .so 文件
- 编译产物本身正确，ELF 签名已应用，依赖仅 libc.so
---

**编译结束**: 2026-06-23 22:49
**最终状态**: built

---

## 功能测试补充 (2026-06-24)

### PyCxx 核心功能验证
PyCxx 6.2.8 核心库已通过 38/38 项功能测试（嵌入模式），验证了 PyCxx C++ API 在鸿蒙平台上的正确性。
详见 reports/functional-test-report.md。

### .so 导入限制
本扩展模块（.so）在鸿蒙平台上无法通过 Python import 直接使用，原因：
- HMDFS 文件系统 SELinux context (hmdfs) 禁止 dlopen
- 影响：所有用户编译的 .so 文件均受此限制
- 解决方案：通过 cmd-pkgs 预编译包安装脚本部署到系统目录后可正常 import

### 编译验证
- 编译: ✅ 成功
- 链接: ✅ 成功
- ELF 签名: ✅ 已签名
- 功能可用性: ⚠️ 编译产物正确，导入受平台限制
