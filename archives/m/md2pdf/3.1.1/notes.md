# md2pdf 3.1.1 适配笔记

## 编译环境
- 构建系统: custom（Python hatchling + pip）
- 编译日期: 2026-05-25
- 编译器: clang/clang++（用于C扩展依赖如cffi/Pillow/brotli）
- 状态: published

## 编译步骤

1. 安装Python依赖（weasyprint, markdown, pygments等）：
   ```bash
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --timeout=300 "cffi>=0.6,<2.0" weasyprint markdown pygments pymdown-extensions python-frontmatter typer hatchling
   ```
2. 构建md2pdf wheel：
   ```bash
   cd $BUILD_SRC_DIR && python3 -m hatchling build
   ```
   产出：dist/md2pdf-3.1.1-py3-none-any.whl
3. 安装到staging（DESTDIR模式）：
   ```bash
   pip install --target=$TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.12/site-packages --no-deps dist/md2pdf-3.1.1-py3-none-any.whl
   ```
   + 创建bin/md2pdf入口脚本
4. 复制所有Python运行时依赖到staging site-packages
5. 签名所有.so文件（PIL/_imaging*.so, _brotli.so, _cffi_backend.so, zopfli.so）
6. 安装到$DEFAULT_PREFIX验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cffi 2.0.0编译失败（ffi.h not found） | cffi 2.0需要ffi.h在标准位置，而鸿蒙libffi安装在/usr/local/include/ffi/ffi.h | 限制cffi版本<2.0（用1.17.1），该版本使用ctypes backend无需编译 |
| 2 | pip下载超时（Pillow 47MB） | 默认PyPI源网络慢 | 使用清华镜像源 -i https://pypi.tuna.tsinghua.edu.cn/simple/ |
| 3 | pip install --root + --prefix报错 | pip不支持同时设置--home和--prefix | 使用--target方式替代DESTDIR模式 |
| 4 | .so文件Permission denied | 鸿蒙ELF签名系统要求 | 用binary-sign-tool sign -inFile ... -outFile ... -selfSign 1签名 |
| 5 | zlib ImportError | LD_LIBRARY_PATH缺少/data/service/hnp/python.org/python_3.12/lib | 添加该路径到LD_LIBRARY_PATH |
| 6 | PKG_CONFIG_PATH缺少cairo/pango | 本地库安装在usr/local/lib/pkgconfig | 添加到PKG_CONFIG_PATH |

## 源码修改

无需修改源码。md2pdf是纯Python包（py3-none-any.whl），所有适配通过环境配置和依赖安装完成。

## 依赖版本

- weasyprint 68.1
- markdown 3.10.2
- pygments 2.20.0
- pymdown-extensions 10.21.3
- python-frontmatter 1.3.0
- typer 0.25.1
- hatchling 1.29.0
- Pillow 12.2.0（本地编译）
- cffi 1.17.1（限制<2.0）
- fonttools 4.63.0
- cairo 1.18.4（C库，已预编译）
- pango 1.50.14（C库，已预编译）
- gdk-pixbuf 2.42.12（C库，已预编译）

## 验证结果

```bash
$ python3 -m pip show md2pdf
Name: md2pdf
Version: 3.1.1
Summary: The Markdown to PDF conversion tool with styles
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| md2pdf-3.1.1-ohos-aarch64.tar.gz | TBD | 预编译包（含md2pdf+Python依赖） |
| md2pdf-3.1.1-ohos-aarch64-debug.tar.gz | TBD | Debug版本 |

## 注意事项

- md2pdf是纯Python包，不生成.a/.so二进制
- DESTDIR模式不适用Python包，使用pip --target替代
- cffi必须限制在<2.0版本（鸿蒙上ffi.h路径不标准）
- watchfiles需要Rust编译器，未安装（可选CLI依赖）
- 所有.so依赖（PIL/cffi/brotli/zopfli）需要ELF签名
---

**编译结束**: 2026-05-25 22:58
**最终状态**: built
