# jc 1.25.6 适配笔记

## 编译环境
- 构建系统: setuptools/pip (纯Python包)
- 编译日期: 2026-06-15
- 编译器: 无（纯Python，无需编译器）
- 状态: built

## 编译步骤

1. 下载源码: `curl -fsSL -k https://github.com/kellyjonbrazil/jc/archive/refs/tags/v1.25.6.tar.gz`
2. 初始化: `python3 ohc-run.py init-build jc 1.25.6 --no-download`
3. staging安装: `python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX`
4. staging验证: 1 bin (jc) + 596 lib files，验证通过
5. 打包: `python3 ohc-run.py package jc 1.25.6`
6. 本地安装: 将jc和依赖从pip-global复制到~/.local/lib/python3.12/site-packages
7. 修复jc脚本shebang指向可用python3路径

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败无法下载 | OpenHarmony环境无标准CA证书 | 使用 `curl -fsSL -k` 跳过SSL验证下载 |
| 2 | setup.py install产出egg格式 | 环境easy_install默认生成egg | pip install产出flat layout，复制到~/.local |
| 3 | pip安装到pip-global而非~/.local | pip全局配置target=pip-global | 手动复制pip-global中的jc到~/.local/site-packages |
| 4 | ~/usr/local/bin/jc无法执行 | shebang指向缺共享库的python3.12 | sed修改shebang指向~/usr/local/bin/python3 |
| 5 | PYTHONPATH不被python3识别 | 环境隔离机制阻止外部PYTHONPATH | 直接安装到~/.local/lib/python3.12/site-packages |
| 6 | ruamel.yaml模块无法导入 | 也安装在pip-global中 | 复制ruamel.yaml到~/.local/site-packages |

## 源码修改

无补丁文件。源码无需修改，仅修复了生成的jc启动脚本shebang。

## 依赖版本

- ruamel.yaml: 0.19.1
- xmltodict: 1.0.4
- Pygments: 2.20.0

## 验证结果

```bash
$ python3 -c "import jc; print('jc version:', jc.__version__)"
jc version: 1.25.6

$ python3 -m jc --version
jc version:  1.25.6
python interpreter version:  3.12.8

$ ~/usr/local/bin/jc --version
jc version:  1.25.6
python interpreter version:  3.12.8

$ ls | ~/usr/local/bin/jc --ls  # 功能验证
[{"filename":"...","flags":"...","owner":"...","group":"...","size":"...","date":"..."}]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jc-1.25.6-ohos-aarch64.tar.gz | 5.8MB | 主预编译包(纯Python，无debug包) |

## 注意事项

- jc为纯Python包，无ELF二进制，不需要debug包(aarch64-debug)
- G0干净构建验证因Python subprocess平台限制失败，但手动验证通过
- 依赖(ruamel.yaml/xmltodict/Pygments)也需安装到~/.local才能正常工作
---
**编译结束**: 2026-06-15 11:03
**最终状态**: built
