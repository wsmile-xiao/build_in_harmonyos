# python-magic

## 软件描述
python-magic 是 libmagic（`file` 命令的底层库）的纯 Python 绑定，用于检测文件类型 / MIME 类型。

## 功能概述
- **文件类型检测**：`magic.from_file(path)` 识别文件真实类型
- **缓冲区检测**：`magic.from_buffer(data)` 识别内存数据
- **MIME 输出**：`mime=True` 时输出 MIME 类型（如 `text/plain`、`image/png`）
- **描述符检测**：`magic.from_descriptor(fd)` 通过文件描述符识别

## OHOS 适配

### 构建方式
- **纯 Python noarch**：无 C/C++ 编译
- `pip install --no-deps --prefix=<staging>` 安装到 staging，打包 `lib/pythonX.Y/site-packages/magic` 到包内

### 关键攻坚点
1. **运行时依赖 libmagic.so.1**：`magic/loader.py` 在 Linux 分支 `ctypes.CDLL('libmagic.so.1')` 加载——`file/5.48.1` Conan 包提供该库，配方 `requires = "file/5.48.1"`
2. **PYTHONPATH 注入**：`package_info()` 把 `lib/pythonX.Y/site-packages` 注入 `env_info.PYTHONPATH`——消费者 `import magic` 可用

### 与 Linux 的差异
- libmagic 由 file 包提供（而非系统 libmagic-dev），消费时需 file 包在运行时依赖链

## 依赖关系
| 依赖 | 版本 | 用途 |
|------|------|------|
| file | 5.48.1 | 提供 libmagic.so.1 运行时库 |

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.4.27 | built | 2026-08-28 | 纯 Python noarch 适配 |

## 参考资料
- 上游仓库: https://github.com/ahupp/python-magic
- PyPI: https://pypi.org/project/python-magic/
