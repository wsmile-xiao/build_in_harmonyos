# docutils 0.23 适配笔记

## 编译环境
- 构建系统: python (pip install)
- 编译日期: 2026-06-01
- 编译器: 无C编译器（纯Python项目）
- 状态: published

## 编译步骤

docutils是纯Python项目，使用 flit 作为构建后端（pyproject.toml），无需传统的 configure/make/make install 流程。

1. **Staging安装（DESTDIR模式）**:
   ```bash
   pip install --no-deps --root=$TEST_PREFIX --prefix=$DEFAULT_PREFIX $BUILD_SRC_DIR
   ```
   文件安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.12/site-packages/docutils/` 和 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/`

2. **本地安装**（模拟用户部署）:
   ```bash
   pip install --no-deps --prefix=$DEFAULT_PREFIX $BUILD_SRC_DIR
   ```

3. **Python路径配置**: 添加 .pth 文件使系统Python能找到非标准路径的site-packages:
   ```bash
   echo "$DEFAULT_PREFIX/lib/python3.12/site-packages" > ~/.local/lib/python3.12/site-packages/docutils-local.pth
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rst2html脚本无法找到docutils模块 | pip --prefix安装到非标准路径，系统Python sys.path不包含该路径 | 在 ~/.local/lib/python3.12/site-packages/ 添加 .pth 文件 |

## 源码修改
无源码修改，无需补丁。

## 依赖版本
- Python 3.12.8（系统预装）
- pip 24.3.1
- flit_core >= 3.11（构建时自动安装）

## 验证结果

```bash
$ rst2html --version
rst2html (Docutils 0.23, Python 3.12.8, on linux)

$ python3 -c "import docutils; print(docutils.__version__)"
0.23

$ echo "Hello World" | rst2html
# 正确输出HTML文档
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| docutils-0.23-ohos-aarch64.tar.gz | 4470KB | 预编译包（纯Python脚本） |

## 注意事项

- docutils是纯Python项目，所有可执行文件都是Python脚本（不是ELF二进制），不需要ELF签名
- 安装后需要在Python的site-packages目录添加 .pth 文件，使系统Python能找到安装的模块
- 构建后端是 flit，不是传统的 setuptools，没有 setup.py
---

**编译结束**: 2026-08-06 07:51
**最终状态**: published
