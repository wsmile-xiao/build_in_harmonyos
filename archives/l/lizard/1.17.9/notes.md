# lizard 1.17.9 适配笔记

## 编译环境
- 构建系统: Python setuptools (setup.py)
- 编译日期: 2026-06-24
- 编译器: 无需编译器（纯 Python 包）
- 状态: published

## 软件概述

lizard 是一个可扩展的代码圈复杂度分析器，支持 C/C++、Java、JavaScript、Python、Go、Rust 等 30+ 种编程语言。纯 Python 实现，无需 C/C++ 编译。

## 编译步骤

1. **下载源码**：从 PyPI 获取 `lizard-1.17.9.tar.gz`
   - URL: `https://files.pythonhosted.org/packages/45/16/.../lizard-1.17.9.tar.gz`
   - 因系统 SSL 证书问题，使用 `curl --insecure` 手动下载

2. **初始化**：`ohc-run.py init-build lizard 1.17.9 --no-download`

3. **Staging 安装**（DESTDIR 模式）：
   ```bash
   cd $BUILD_SRC_DIR
   python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX
   ```
   - 使用 `--root` 等效于 DESTDIR
   - 产物：bin/lizard + lib/python3.12/site-packages/（114 个文件）

4. **打包**：`ohc-run.py package lizard 1.17.9` → `lizard-1.17.9-ohos-aarch64.tar.gz` (521KB)

5. **本地安装**：`python3 setup.py install --prefix=$DEFAULT_PREFIX --old-and-unmanageable`
   - 使用 `--old-and-unmanageable` 避免生成 zip egg（zip egg 无法被系统 Python 搜索到）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 SSL 失败 | 系统缺少 CA 证书 | `curl --insecure` 手动下载，再 `init-build --no-download` |
| 2 | lizard 命令 PackageNotFoundError | egg 安装为 zip 格式，系统 Python 不搜索 `~/usr/local/lib/python3.12/site-packages/` | 1) `--old-and-unmanageable` 生成扁平结构；2) 替换 wrapper 脚本，在启动时 `sys.path.insert` 添加 site-packages |
| 3 | 17 个测试 ImportError | 测试使用相对导入 `from .testHelpers import ...`，`unittest discover` 默认不从根目录运行 | 从项目根目录运行 `python3 -m unittest discover -s test -t .` |
| 4 | 5 个测试 ModuleNotFoundError | sdist tarball 缺少 `test/helper_stream.py` 和 `test/data/utf.c` | 上游 sdist 问题，不影响功能 |

## 源码修改

无源码修改。安装时替换了 `bin/lizard` 入口脚本（原为 easy-install entry script，替换为直接 import 的 wrapper），以适配本平台 Python 路径搜索。

### wrapper 脚本（bin/lizard）

```python
#!/data/service/hnp/python.org/python_3.12/bin/python3.12
import sys
import os
_PREFIX = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
_SITE = os.path.join(_PREFIX, 'lib', 'python3.12', 'site-packages')
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)
from lizard import main
main()
```

## 依赖

- Python 3.8+（本平台预装 3.12）
- 无 C/C++ 依赖
- 测试需要 mock（已通过 pip 安装）和 pytest（网络超时未安装，5 个测试跳过）

## 验证结果

```bash
$ lizard --version
1.17.9

$ lizard test_sample.c
================================================
  NLOC    CCN   token  PARAM  length  location
------------------------------------------------
       6      2     21      1       6 simple_function@1-6@test_sample.c
      14      4     70      3      14 complex_function@8-21@test_sample.c
1 file analyzed.
```

单元测试：214 个测试，207 通过，5 错误（测试文件缺失），2 跳过。

---

**编译开始**: 2026-06-24
**编译结束**: 2026-06-24
**最终状态**: published — 编译安装成功，功能验证通过
