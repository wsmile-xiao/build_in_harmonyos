# binwalk 2.3.4 适配笔记

## 编译环境
- 构建系统: Python (setuptools)
- 编译日期: 2026-06-05
- 编译器: 无需编译器（纯 Python 项目）
- 状态: built

## 编译步骤

1. 源码获取：从 GitHub 克隆 binwalk v2.3.4
2. 打包源码为 tar.gz 格式
3. 使用 ohc-run.py init-build 初始化编译环境
4. 使用 pip 安装到本地 site-packages 目录:
   ```bash
   python3 -m pip install --target=$HOME/usr/local/lib/python3.12/site-packages .
   ```
5. 创建 wrapper script 作为 binwalk 命令入口

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | binwalk v3 (Rust版本) 无法编译 | Rust 工具链依赖 glibc 动态链接器，鸿蒙使用 musl | 使用 binwalk v2.3.4 (Python版本) 替代 |
| 2 | Python 3.12 不支持 `imp` 模块 | `imp` 模块在 Python 3.12 已移除 | 修改 plugin.py 和 module.py，使用 importlib.util 替代 |
| 3 | pip 命令不可用 | pip 未安装为独立命令 | 使用 `python3 -m pip` 替代 |

## 源码修改

- `src/binwalk/core/plugin.py`: 替换 `import imp` 为 `import importlib.util`，修改 `imp.load_source()` 为 `importlib.util.spec_from_file_location()` + `module_from_spec()` + `exec_module()`
- `src/binwalk/core/module.py`: 同上修改

## 依赖版本

- Python 3.12.8（系统自带）
- 无其他编译依赖

## 验证结果

```bash
$ binwalk --help
Binwalk v2.3.3+cddfede
Craig Heffner, ReFirmLabs
https://github.com/ReFirmLabs/binwalk

Usage: binwalk [OPTIONS] [FILE1] [FILE2] [FILE3] ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| binwalk wrapper script | ~100 bytes | bash wrapper 调用 python3 -m binwalk |
| binwalk package | ~135KB | Python wheel 包 |

## 注意事项

1. binwalk 是纯 Python 项目，无需编译，只需安装
2. 需要修改源码以兼容 Python 3.12（imp 模块已移除）
3. wrapper script 需使用鸿蒙的 bash 路径：`/data/service/hnp/bin/bash`
4. v3 (Rust版本) 在鸿蒙上无法编译，需要使用 v2 (Python版本)

---

**编译结束**: 2026-06-05 10:55
**最终状态**: built
---

**编译结束**: 2026-06-05 10:57
**最终状态**: built
