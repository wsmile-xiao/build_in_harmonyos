# keyring 25.6.0 适配笔记

## 编译环境
- 构建系统: custom (pure Python wheel extraction)
- 编译日期: 2026-06-12
- 编译器: N/A (pure Python, no C compilation)
- 状态: built

## 编译步骤

keyring 是纯 Python 包，无需 C 编译。使用 wheel 文件手动解压安装：

1. 从阿里云 PyPI 镜像下载 keyring-25.6.0-py3-none-any.whl
2. 解压 .whl 文件到 site-packages 目录（3个位置）：
   - DESTDIR staging: $TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.14/site-packages/
   - $DEFAULT_PREFIX: /storage/Users/currentUser/usr/local/lib/python3.14/site-packages/
   - harmonybrew: /storage/Users/currentUser/.harmonybrew/lib/python3.14/site-packages/
3. 同样方式安装所有依赖包的 wheel 文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip 超时/挂起 | 中国网络环境下 pip 连接 PyPI 超时 | 使用阿里云镜像手动下载 .whl 文件 |
| 2 | GitHub 下载超时 | 中国网络无法直连 GitHub | 使用阿里云 PyPI mirror 的 .whl 文件 |
| 3 | jaraco.context 1.7 缺少 ExceptionTrap.passes | keyring 25.6.0 需要更新的 jaraco.context | 升级到 jaraco.context 6.0.1 |
| 4 | jaraco.classes 版本不兼容 | 旧版 jaraco.classes 与 keyring 25.6.0 不兼容 | 升级到 jaraco.classes 3.3.1 |
| 5 | more-itertools 缺失 | jaraco.context 6.0.1 依赖 more-itertools | 安装 more_itertools 11.1.0 |
| 6 | G0 clean build 验证失败 | keyring 无 configure/Makefile（纯 Python） | 手动验证通过，G0 不适用于纯 Python 包 |
| 7 | keyring.__version__ 不存在 | keyring 25.6.0 不定义 __version__ 属性 | 使用 importlib.metadata.version('keyring') |

## 源码修改

无补丁，无源码修改。直接使用 PyPI 发布的 wheel 文件。

## 依赖版本

- keyring 25.6.0
- jaraco.classes 3.3.1
- jaraco.functools 3.7.0 (was 1.12, upgraded)
- jaraco.context 6.0.1 (was 1.7, upgraded)
- more-itertools 11.1.0
- Python 3.14.5 (harmonybrew)

## 验证结果

```bash
$ python3 -c "from importlib.metadata import version; print('keyring version:', version('keyring'))"
keyring version: 25.6.0
```

## 交付物

Staging directory: /data/storage/el2/base/cache/test-install-keyring-25.6.0/
Installed packages in site-packages across 3 prefixes

## 注意事项

1. 纯 Python 包 - ohc-run.py 的 autotools/cmake 构建流程不适用
2. 需手动下载 .whl 文件并解压到 site-packages
3. keyring.__version__ 属性不存在，需使用 importlib.metadata
4. 必须安装完整依赖链：jaraco.classes → jaraco.functools → jaraco.context → more-itertools

---

**编译结束**: 2026-06-12 02:10
**最终状态**: built