# aubio 0.4.9 适配笔记

## 编译环境
- 构建系统: waf (bundled v2.0.14, patched for Python 3.12)
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码（通过 pip download 获取，因 GitHub 直连超时）
2. `ohc-run.py init-build aubio 0.4.9 --url=... --no-download`
3. 修复 waflib Python 3.12 兼容性问题（3个文件）
4. `python3 ./waf configure --prefix=$DEFAULT_PREFIX --disable-jack --disable-avcodec --disable-samplerate`
5. `python3 ./waf build` — 48/48 测试全部通过
6. `python3 ./waf install --destdir=$TEST_PREFIX`
7. `python3 ./waf install --prefix=$DEFAULT_PREFIX` (不带 DESTDIR)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ModuleNotFoundError: No module named 'imp'` | Python 3.12 移除了 `imp` 模块 | 替换 `imp.new_module()` 为 `types.ModuleType()`，移除 `import imp` |
| 2 | `ValueError: invalid mode: 'rUb'` | Python 3.12 移除了文件打开的 'U' 模式标志 | 在 Utils.readf() 中添加 `m=m.replace('U','')` |
| 3 | `import imp;print(imp.get_tag())` 在 waf configure 中失败 | `imp.get_tag()` 在 Python 3.12 中不可用 | 替换为 `sysconfig.get_config_var('EXT_SUFFIX').split('.')[-2]` |
| 4 | GitHub 源码下载超时 | 网络限制 | 通过 pip download 获取源码 |

## 源码修改

| 补丁文件 | 修改文件 | 修改内容 |
|----------|----------|----------|
| 0001-waflib-Context.py.patch | waflib/Context.py | `import imp` → `import types`; `imp.new_module()` → `types.ModuleType()`; `'rU'` → `'r'` |
| 0002-waflib-Tools-python.py.patch | waflib/Tools/python.py | `imp.get_tag()` → `sysconfig` 方式获取 PYTAG |
| 0003-waflib-Utils.py.patch | waflib/Utils.py | 在 `readf()` 中移除 'U' 模式标志 |

## 依赖版本

- Python 3.12.8（运行环境）
- clang 15.0.4
- 无外部依赖（aubio 使用内置 ooura FFT）

## 验证结果

```bash
$ pkg-config --modversion aubio
0.4.9

$ LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib aubioonset --help
# 正常输出使用说明

# waf build 测试结果: 48/48 pass
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aubio-0.4.9-ohos-aarch64.tar.gz | 2263KB | 预编译包（stripped） |
| aubio-0.4.9-ohos-aarch64-debug.tar.gz | 1306KB | 预编译包（含debug符号） |
| 0001-waflib-Context.py.patch | ~2KB | Python 3.12 compat: Context.py |
| 0002-waflib-Tools-python.py.patch | ~1KB | Python 3.12 compat: python.py |
| 0003-waflib-Utils.py.patch | ~1KB | Python 3.12 compat: Utils.py |

## 注意事项

- aubio 的命令行工具不支持 --version 参数，只支持 --help
- aubio 内置 ooura FFT 实现，不需要外部 fftw3 依赖即可编译核心功能
- 如需 fftw3/sndfile/jack/avcodec/samplerate 支持，需先安装对应预编译包再 configure
- waf 2.0.14 与 Python 3.12+ 不兼容，必须先应用补丁才能运行
---

**编译结束**: 2026-05-25 22:50
**最终状态**: published
