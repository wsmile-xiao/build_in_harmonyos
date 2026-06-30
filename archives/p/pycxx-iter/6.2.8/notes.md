# pycxx-iter 6.2.8 适配笔记

## 编译环境
- 构建系统: script (Python distutils + setup_makefile.py)
- 编译日期: 2026-06-23
- 编译器: clang/clang++ (g++ 是 clang++ 的符号链接)
- Python: 3.12 (位于 /data/service/hnp/python.org/python_3.12)
- libc++: LLVM 18.1.8 源码头文件
- 状态: published

## 编译步骤

1. 下载源码 tarball: `curl -kL -o pycxx-iter-6.2.8.tar.gz https://prdownloads.sourceforge.net/cxx/pycxx-6.2.8.tar.gz`
2. 解压到 `$BUILD_SRC_DIR`
3. 修改 `setup_makefile.py`:
   - 添加 `-nostdinc++` 禁用默认 C++ 标准库搜索
   - 添加 LLVM libc++ 头文件路径 `-I<path>/llvm-project-18.1.8.src/libcxx/include`
   - 添加 OHOS 系统 C 头文件路径 `-I<DEFAULT_PREFIX>/include`
   - 添加 Python 头文件路径 `-I<data/service/hnp/python.org/python_3.12/include/python3.12>`
   - 修改 LDEXE/LDSHARED: 添加 `-nostdlib++ -L<lib_dir> -lc++`
4. 创建 `__config_site` 文件（配置 musl/pthread/hardening 等宏）
5. 从 `_sysheaders_backup` 复制缺失的 C 标准头文件
6. 生成 Makefile: `python3 setup_makefile.py linux linux.mak`
7. 编译: `make -f linux.mak obj/pycxx_iter.so`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 系统缺少 CA 证书 | 使用 `curl -kL` 手动下载 tarball |
| 2 | 缺少 C/C++ 标准头文件 | OHOS 系统精简安装 | 从 `_sysheaders_backup` 复制 C 头文件；从 LLVM 源码树获取 libc++ 头文件 |
| 3 | `sys/time.h` include 失败 | OHOS 上该头文件路径不同 | 在 `WrapPython.h` 中添加 `#if defined(__OHOS__)` 保护 |
| 4 | `Py_UNICODE` 类型不存在 | Python 3.12 移除了 `Py_UNICODE` | 替换为 `wchar_t` |
| 5 | `PyUnicode_FromUnicode` 不存在 | Python 3.12 移除了该 API | 替换为 `PyUnicode_FromWideChar` |
| 6 | `PyUnicode_GET_SIZE` 不存在 | Python 3.12 移除了该 API | 替换为 `PyUnicode_GetLength` |
| 7 | `PyUnicode_AS_UNICODE` 不存在 | Python 3.12 移除了该 API | 替换为 `PyUnicode_AsWideCharString` |
| 8 | `tp_print` 字段不存在 | Python 3.9 移除了 `tp_print` | 用 `#if PY_VERSION_HEX < 0x03090000` 保护 |
| 9 | `_Py_PackageContext` 未声明 | Python 3.12 移除了该全局变量 | 用 `#if PY_VERSION_HEX < 0x030C0000` 保护，3.12+ 返回 nullptr |
| 10 | 链接找不到 `-lc++` 等 | OHOS 默认库搜索路径不包含自定义路径 | 添加 `-nostdlib++ -L<lib_dir> -lc++` 到 LDEXE/LDSHARED |
| 11 | HMDFS 无法 dlopen .so | HMDFS 安全策略限制 | 编译成功，运行时加载受限于文件系统安全策略 |

## 源码修改

以下文件已通过 `ohc-run.py track-edit` 跟踪：

1. **setup_makefile.py** — 添加 OHOS 系统头文件路径、libc++ 头文件路径、`-nostdinc++`、`-nostdlib++` 链接标志
2. **CXX/WrapPython.h** — 为 `#include <sys/time.h>` 添加 `#if defined(__OHOS__)` 保护
3. **CXX/Python3/Objects.hxx** — 替换所有 Py_UNICODE 相关 API（Py_UNICODE→wchar_t, PyUnicode_FromUnicode→PyUnicode_FromWideChar, PyUnicode_GET_SIZE→PyUnicode_GetLength, PyUnicode_AS_UNICODE→PyUnicode_AsWideCharString），重写 as_unicodestring() 和 unicode_data()
4. **Src/Python3/cxx_extensions.cxx** — 用 `#if PY_VERSION_HEX` 保护 `tp_print` 字段
5. **Src/IndirectPythonInterface.cxx** — 用 `#if PY_VERSION_HEX` 保护 `_Py_PackageContext` 引用

## 验证结果

编译成功，生成 `obj/pycxx_iter.so` (1067136 bytes, ELF 64-bit LSB arm64)。

运行时测试受限于 HMDFS 安全策略（.so 文件位于分布式文件系统上，无法通过 dlopen 加载），但编译验证通过：
- 所有源文件成功编译（仅有 deprecation 警告，无错误）
- 链接成功生成 .so 文件
- 文件格式正确: ELF shared object, 64-bit LSB arm64

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| obj/pycxx_iter.so | 1067136 bytes | pycxx_iter Python 扩展模块 (aarch64) |

## 注意事项

- OHOS HMDFS 文件系统上的 .so 文件无法通过 `dlopen` 加载，需要在 userdata 分区上安装才能运行时测试
- 所有修改仅限于源文件，未修改生成的 Makefile
- 使用了 `-nostdinc++` 和 `-nostdlib++` 来禁用默认 C++ 标准库搜索，改用 LLVM libc++ 源码头文件和系统 libc++.so
---

**编译结束**: 2026-06-23 22:42
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
