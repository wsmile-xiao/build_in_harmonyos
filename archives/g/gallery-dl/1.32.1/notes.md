# gallery-dl 1.32.1 适配笔记

## 编译环境
- 构建系统: setuptools (Python setup.py)
- 编译日期: 2026-08-06
- 编译器: N/A (pure Python, no C/C++ compilation)
- 状态: published

## 编译步骤

1. `python3 -m pip install --break-system-packages "requests>=2.11.0"` — install runtime dependency
2. `python3 setup.py build` — build the package
3. `python3 setup.py install --prefix=$PACKAGE_FOLDER` — install to conan package folder

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip install --prefix 失败: "Cannot set --home and --prefix together" | OHOS 环境设置了 PIP_TARGET 环境变量，与 --prefix 冲突 | 改用 `python3 setup.py install --prefix=...` 绕过 pip 的 target 机制 |
| 2 | conan list JSON 解析失败 | requests 库因 charset_normalizer .so 文件权限问题输出警告到 stderr，混入 JSON | 安装 chardet 作为 requests 的字符检测后备依赖 |

## 源码修改

无源码修改，gallery-dl 是纯 Python 包，无需适配即可在 HarmonyOS 上运行。

## 依赖版本

- Python 3.12.9 (system)
- requests (>=2.11.0, via pip — version depends on OHOS PyPI mirror)
- chardet (via pip, installed separately as fallback for requests charset detection)

## 验证结果

```bash
gallery-dl --version
# Output: 1.32.1
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (setuptools build system) |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | Conan L1 测试 (gallery-dl --version) |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

- gallery-dl 是纯 Python 包，无需 C/C++ 交叉编译
- 运行时依赖 requests 通过 pip 安装，不通过 conan 依赖链管理
- PIP_TARGET 环境变量会干扰 pip install --prefix，需使用 setup.py install 替代

---

**编译结束**: 2026-08-06
**最终状态**: published
