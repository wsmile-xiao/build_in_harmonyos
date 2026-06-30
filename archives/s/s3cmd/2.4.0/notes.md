# s3cmd 2.4.0 适配笔记

## 编译环境
- 构建系统: python (pip install)
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built
- Python版本: 3.14.5 (harmonybrew)

## 编译步骤

1. **下载源码**: 从 PyPI 获取 s3cmd-2.4.0.tar.gz
2. **init-build**: `ohc-run.py init-build s3cmd 2.4.0 --url=<pypi_url>`
3. **安装依赖**: pip install python-dateutil python-magic (s3cmd运行依赖)
4. **DESTDIR模式安装**: `pip3 install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX --no-deps .`
5. **本地安装验证**: `pip3 install --prefix=$DEFAULT_PREFIX --no-deps --break-system-packages .`
6. **验证**: `/storage/Users/currentUser/usr/local/bin/s3cmd --version` → `s3cmd version 2.4.0`
7. **打包**: `ohc-run.py package s3cmd 2.4.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 全自动build安装无产物 | ohc-run.py build Step 5 对Python项目使用make install DESTDIR模式，但Python项目没有make install | 手动使用 pip install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX DESTDIR模式 |
| 2 | s3cmd --version 报 ModuleNotFoundError: No module named 'S3' | pip install --prefix=$DEFAULT_PREFIX 将S3包安装到$DEFAULT_PREFIX/lib/python3.14/site-packages，但harmonybrew Python不会搜索该路径 | 修改s3cmd脚本，添加 sys.path.insert(0, ...) 以动态添加site-packages路径 |
| 3 | pip install报 externally-managed-environment (PEP 668) | harmonybrew Python标记为externally-managed | 使用 --break-system-packages 标志 |
| 4 | LD_LIBRARY_PATH缺失导致SSL模块加载失败 | _ssl.cpython-314.so找不到libcrypto.so.3 | 设置 LD_LIBRARY_PATH=/storage/Users/currentUser/.harmonybrew/lib |

## 源码修改

- **s3cmd**: 添加 sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))), "lib", "python3.14", "site-packages"))
  - 补丁: 0001-s3cmd.patch
  - 类型: 平台适配 (platform_only=True)
  - 原因: OHOS Python不搜索$DEFAULT_PREFIX的site-packages路径

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| python-dateutil | 2.9.0.post0 | s3cmd运行依赖 |
| python-magic | 0.4.27 | s3cmd运行依赖 |
| six | 1.17.0 | python-dateutil依赖 |

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/s3cmd --version
s3cmd version 2.4.0
```

## 交付物

| 文件 | 说明 |
|------|------|
| s3cmd-2.4.0-r1-ohos-aarch64.tar.gz | 预编译包 (Python项目，包含s3cmd脚本和S3模块) |

## 注意事项

- s3cmd是纯Python项目，没有C/C++编译步骤，直接pip install即可
- Python项目的DESTDIR模式必须使用pip install --prefix --root，不能使用make install DESTDIR
- Python项目打包时不含ELF二进制，verify-build G1/G3检查应为空（纯Python脚本）
- s3cmd运行需要python-dateutil和python-magic依赖，用户需先安装这些Python包
- OHOS适配核心：Python解释器不会搜索$DEFAULT_PREFIX的site-packages，需sys.path.insert适配
---

**编译结束**: 2026-06-03 17:39
**最终状态**: built
