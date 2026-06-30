# pdfalyzer 1.19.6 适配笔记

## 编译环境
- 构建系统: python (pip install)
- 编译日期: 2026-05-25
- Python版本: 3.12.8
- 状态: published

## 编译步骤

pdfalyzer 是纯 Python 包（Poetry 构建），无 setup.py/setup.cfg，仅 pyproject.toml。

1. **依赖安装**：先安装核心依赖 yara-python（C扩展，需编译 libyara）
   - `python3 -m pip install --target=$DEFAULT_PREFIX/lib/python3.12/site-packages -i https://pypi.tuna.tsinghua.edu.cn/simple/ yara-python>=4.5.4`
2. **pdfalyzer 安装**：pip install --target DESTDIR
   - `python3 -m pip install --target=$DESTDIR_SITE_PKGS -i https://pypi.tuna.tsinghua.edu.cn/simple/ pdfalyzer==1.19.6`
3. **脚本安装**：pip --target 模式在 site-packages/bin/ 生成入口脚本，需移动到 $DEFAULT_PREFIX/bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip --prefix + --home 冲突 | pip 版本 bug | 使用 --target 替代 --prefix |
| 2 | PyPI 下载超时 | 网络不稳定 | 使用清华镜像 pypi.tuna.tsinghua.edu.cn |
| 3 | yara-python 编译耗时 | 内嵌 libyara C 源码编译 | 正常等待约7分钟 |

## 源码修改

无需修改源码。pdfalyzer 是纯 Python 包，所有依赖通过 pip 安装。

## 依赖版本

- yara-python 4.5.4 (C扩展，包含 libyara 编译)
- yaralyzer 1.3.17
- anytree 2.13.0
- pypdf 6.6.0
- rich 14.2.0
- chardet 5.2.0
- python-dotenv 1.2.2
- rich-argparse-plus 0.3.1.4
- markdown-it-py 4.2.0
- pygments 2.20.0
- mdurl 0.1.2
- poetry-core 2.4.1

## 验证结果

```bash
# pdfalyze 入口点可用
$DEFAULT_PREFIX/bin/pdfalyze --help
# Python import 可用 (需设置 PYTHONPATH)
python3 -c "import pdfalyzer; print(pdfalyzer.__version__)"
```

## 交付物

| 文件 | 说明 |
|------|------|
| pdfalyzer-1.19.6-ohos-aarch64.tar.gz | Release 包 (含 pdfalyzer + 所有依赖) |
| pdfalyzer-1.19.6-ohos-aarch64-debug.tar.gz | Debug 包 (含调试符号) |

## 注意事项

- yara.cpython-312.so 是唯一需要 ELF 签名的 native 模块
- Python 包不需要 strip/RPATH 处理（纯 Python 部分）
- 安装后需设置 PYTHONPATH 才能 import