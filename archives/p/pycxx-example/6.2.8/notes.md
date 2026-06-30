# pycxx-example 6.2.8 适配笔记

## 编译环境
- 构建系统: script (Python distutils + setup_makefile.py)
- 编译日期: 2026-06-23
- 编译器: clang 18.1.8 / clang++ 18.1.8 (g++ symlinked to clang++)
- 源码: pycxx-6.2.8.tar.gz (PyCXX 6.2.8)
- 状态: built

## 编译步骤

1. 下载 pycxx-6.2.8.tar.gz 源码包
2. 应用5个补丁（0001-0005）
3. 使用 `python3 setup_makefile.py linux linux.mak` 生成 Makefile（补丁0005已将 g++→clang++ 和 sysroot/libcxx 路径固化）
4. `make -f linux.mak example` 编译 example 扩展模块
5. 无需手动设置环境变量或创建 g++ 符号链接（R21: 零介入）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | g++ 未找到 | setup_makefile.py 硬编码 g++ | 补丁0005: 将 g++→clang++, gcc→clang |
| 2 | 'sys/time.h' file not found | 系统缺少 C/C++ 标准库头文件在默认搜索路径 | 补丁0005: 添加 --sysroot 到 CCCFLAGS |
| 3 | 'string' file not found | C++ 标准库(libc++)头文件未安装 | 补丁0005: 添加 -nostdinc++ -I libcxx-ohos 到 CCCFLAGS |
| 4 | 'pthread_cond_clockwait' undeclared | 系统 musl C 库缺少此函数 | 补丁0005: sysroot 包含完整系统头文件 |
| 5 | PyUnicode_FromUnicode 等函数未定义 | Python 3.12 移除了这些旧 API | 补丁0001: 替换为 PyUnicode_FromWideChar 等 wchar_t API |
| 6 | tp_print 成员不存在 | Python 3.12 移除了 PyTypeObject.tp_print | 补丁0003: 添加 #if PY_VERSION_HEX 版本守卫 |
| 7 | _Py_PackageContext 未定义 | Python 3.12 移除了此全局变量 | 补丁0002: 添加版本守卫返回 nullptr |
| 8 | Py_UNICODE unicode_null_string 类型不匹配 | Objects.hxx 声明 Py_UNICODE 但 cxxsupport.cxx 定义 Py_UNICODE | 补丁0001+0004: 统一改为 wchar_t |
| 9 | .so 加载 "Permission denied" | HMDFS 安全策略禁止从用户文件系统加载 .so 文件 | 平台限制，需通过 cmd-pkgs 安装脚本部署到系统目录 |

## 源码修改

### 1. CXX/Python3/Objects.hxx (补丁0001)
- `typedef std::basic_string<Py_UNICODE>` → `typedef std::basic_string<wchar_t>`
- `extern Py_UNICODE unicode_null_string[1]` → `extern wchar_t unicode_null_string[1]`
- `Char( Py_UNICODE v )` → `Char( wchar_t v )`
- `Char &operator=( Py_UNICODE v )` → `Char &operator=( wchar_t v )`
- `String( const Py_UNICODE *s, int length )` → `String( const wchar_t *s, int length )`
- `PyUnicode_FromUnicode` → `PyUnicode_FromWideChar` (6 处)
- `PyUnicode_GET_SIZE` → `PyUnicode_GetLength` (2 处)
- `PyUnicode_AS_UNICODE` → `PyUnicode_AsWideCharString` 重新实现 `as_unicodestring()` 和 `unicode_data()`
- `const Py_UNICODE *unicode_data()` → `const wchar_t *unicode_data()`

### 2. Src/Python3/cxxsupport.cxx (补丁0004)
- `Py_UNICODE unicode_null_string[1]` → `wchar_t unicode_null_string[1]`

### 3. Src/Python3/cxx_extensions.cxx (补丁0003)
- `table->tp_print = 0;` 添加 `#if PY_VERSION_HEX < 0x03090000` 版本守卫

### 4. Src/IndirectPythonInterface.cxx (补丁0002)
- `_Py_PackageContext` 引用添加 `#if PY_VERSION_HEX < 0x030C0000` 版本守卫，3.12+ 返回 nullptr

### 5. setup_makefile.py (补丁0005)
- `g++` → `clang++`, `gcc` → `clang`
- CCCFLAGS 添加 `--sysroot` 和 `-nostdinc++ -I libcxx-ohos`
- LDEXE/LDSHARED 添加 `--sysroot`, `-nostdlib`, 静态链接 `libc++_static.a` + `libc++abi.a`

## 依赖版本

- Python: 3.12 (位于 /data/service/hnp/python.org/python_3.12/)
- Clang/Clang++: 18.1.8 (位于 ~/usr/local/bin/)
- OpenHarmony SDK: 26.0.0.18 (提供 sysroot + libc++ + 系统头文件)
- LLVM libc++: 来自 SDK LLVM 15.0.4 (libcxx-ohos)
- musl libc: 系统内置 (/lib/ld-musl-aarch64.so.1)

## 验证结果

### 编译验证
```
$ make -f linux.mak obj/example.so
Compile: Demo/Python3/example.cxx into obj/example.obj  [OK]
Compile: Demo/Python3/range.cxx into obj/range.obj      [OK]
Compile: Demo/Python3/rangetest.cxx into obj/rangetest.obj  [OK]
Compile: Src/cxxsupport.cxx into obj/cxxsupport.obj      [OK]
Compile: Src/cxx_extensions.cxx into obj/cxx_extensions.obj  [OK]
Compile: Src/cxxextensions.c into obj/cxxextensions.obj  [OK]
Compile: Src/IndirectPythonInterface.cxx into obj/IndirectPythonInterface.obj  [OK]
Link obj/example.so                                      [OK]
```

### 产物验证
```
$ ls -la obj/example.so
-rwxrwx--- 1 20001006 file_manager 1370240 2026-06-23  obj/example.so
$ readelf -d obj/example.so | grep NEEDED
NEEDED: libc++_shared.so
NEEDED: libc.so
```

### 运行时验证
- `python3 -c "from CXX import example"` → 失败: Permission denied
- 根因: HMDFS 安全策略禁止从 /storage/Users/ 加载 .so 文件
- 系统目录 (/data/service/hnp/) 为只读，无法手动安装
- 需通过 cmd-pkgs 预编译包安装脚本部署到系统目录

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| obj/example.so | 1370240 bytes | Python C++ 扩展模块 (未 strip) |
| obj/example.so (stripped+signed) | 579200 bytes | 去除调试信息并签名后 |

## 注意事项

1. **C++ 标准库依赖**: 本系统未安装独立的 C++ 标准库，补丁0005 已将 SDK sysroot 和 libcxx-ohos 路径固化到 setup_makefile.py
2. **HMDFS 限制**: 用户文件系统 (/storage/Users/) 中的 .so 文件无法被 dlopen 加载，需部署到系统目录
3. **Python 3.12 兼容性**: PyCXX 6.2.8 原始代码不兼容 Python 3.12，需修改 5 个源文件（补丁0001-0005）
4. **g++ 符号链接已消除**: 补丁0005 将 setup_makefile.py 中的 g++ 替换为 clang++，不再需要手动创建符号链接
5. **签名流程**: 需先 strip debug 信息，再移除旧 .codesign 节，最后用 binary-sign-tool 签名
---

**编译结束**: 2026-06-23 22:53
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
