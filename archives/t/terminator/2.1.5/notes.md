# terminator 2.1.5 适配笔记

## 编译环境
- 构建系统: setuptools (setup.py) — pure Python application
- 编译日期: 2026-07-02
- 编译器: N/A (Python package, no C/C++ compilation)
- Python: 3.14.6
- 状态: published

## 编译步骤

```bash
# 1. Install setuptools
pip3 install --break-system-packages setuptools

# 2. Build with --without-gettext (intltool-merge not available on OHOS)
cd $BUILD_SRC_DIR
python3 setup.py --without-gettext build

# 3. Install to staging prefix
python3 setup.py --without-gettext install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX --no-compile

# 4. Verify import
PYTHONPATH=$TEST_PREFIX/.../site-packages python3 -c "import terminatorlib; from terminatorlib.version import APP_NAME, APP_VERSION; print(f'{APP_NAME} {APP_VERSION}')"
# Output: terminator 2.1.5
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | setuptools not installed | Fresh Python 3.14.6 installation | `pip3 install --break-system-packages setuptools` |
| 2 | intltool-merge not found | OHOS does not ship intltool | Use `--without-gettext` flag; setup.py falls back to stripping `_` chars from .desktop.in files |
| 3 | PEP 668 blocks pip install | Externally-managed Python environment | Use `--break-system-packages` flag |
| 4 | psutil not in community PyPI mirror | Mirror missing psutil package | Installed from official pypi.org |
| 5 | pycairo/PyGObject require system GTK/cairo libs | Native C extensions needing system libraries | Not installed; listed as runtime deps in conanfile.py, not build deps |

## 源码修改

无源码修改。使用 `--without-gettext` 标志跳过 gettext/intltool 依赖。

## 依赖版本

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
| setuptools | 80.9.0 | pip3 install |
| configobj | 5.0.9 | pip3 install (runtime dep) |
| psutil | 7.2.2 | pip3 install from pypi.org (runtime dep) |

### 未安装的运行时依赖（需系统库支持）

| 依赖 | 原因 |
|------|------|
| pycairo | Requires cairo system library (C extension) |
| dbus-python | Requires dbus system library (C extension) |
| pygobject | Requires gobject-introspection system library (C extension) |

## 验证结果

```bash
$ python3 -c "from terminatorlib.version import APP_NAME, APP_VERSION; print(f'{APP_NAME} {APP_VERSION}')"
terminator 2.1.5

$ python3 -c "import terminatorlib; print('Import OK:', terminatorlib.__file__)"
Import OK: .../site-packages/terminatorlib/__init__.py
```

## 注意事项

- terminator 是 Python GTK/VTE 桌面 GUI 应用，不是 C/C++ 库
- 构建使用 `--without-gettext` 跳过 intltool-merge 依赖（OHOS 不提供）
- pycairo, dbus-python, pygobject 需要系统 GTK/cairo/dbus 库，无法通过 pip 直接安装
- conanfile.py 使用 `pip install` 模式（通过 setup.py install），package_info 设置 PYTHONPATH
- R32: settings.os 判断使用 `in ("Linux", "OHOS")`，本 recipe 使用 settings = ("os", "arch") 简化
- R40: GTK/VTE 图形栈适配需人工确认——test_package 仅验证 Python import，未验证 GTK 窗口渲染功能
---

**编译结束**: 2026-07-02 09:57
**最终状态**: published
