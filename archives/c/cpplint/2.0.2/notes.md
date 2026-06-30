# cpplint 2.0.2 适配笔记

## 编译环境
- 构建系统: python (setuptools/pip)
- 编译日期: 2026-06-30
- 编译器: clang/clang++ (not used — pure Python tool)
- 状态: published

## 编译步骤

cpplint 是一个纯 Python 命令行工具，无需 C/C++ 编译。

1. 从 PyPI 下载源码 sdist: `pip3 download cpplint==2.0.2 --no-binary :all:`
2. 使用 pip 安装到 staging 目录:
   ```bash
   python3 -m pip install . --target=$TEST_PREFIX/usr/local/lib/python3.12/site-packages
   ```
3. 创建入口脚本到 `$TEST_PREFIX/usr/local/bin/cpplint`
4. 运行测试: `python3 -m pytest cpplint_unittest.py`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 环境无法直接访问 github.com | 从 PyPI 社区源下载 sdist |
| 2 | /tmp 只读 (E002) | 鸿蒙平台 /tmp 为只读文件系统 | 使用 $HOME/tmp 作为临时目录 |
| 3 | conan-init 生成 Autotools 模板 | 模板系统不识别 Python 项目 | 手动重写 conanfile.py 为 Python 安装方式 |
| 4 | conandata.yml sha256 为占位符 | conan-init 未自动计算 | 手动填入实际 SHA256 |
| 5 | test_package 使用 Conan 1 API | 自动生成模板使用旧 API | 重写为 Conan 2 VirtualRunEnv 方式 |
| 6 | G1 失败: 缺少补丁应用调用 | conanfile.py 无 apply_conandata_patches | 添加 apply_conandata_patches(self) 到 build() |

## 源码修改

无源码修改。cpplint 开箱即用，纯 Python 脚本。

## 依赖版本

- Python 3.12.9
- conan 2.29.1 (OHOS 适配版)
- 无第三方编译依赖

## 验证结果

```bash
# 单元测试
$ python3 -m pytest cpplint_unittest.py
205 passed in 7.32s
Coverage: 92.42%

# 版本验证
$ cpplint --version
Cpplint fork (https://github.com/cpplint/cpplint)
cpplint 2.0.2

# Conan 验证
$ ohc-run.py conan-verify cpplint 2.0.2
G0: PASS, G1: PASS, G2: PASS, G3: PASS, G4: PASS
L2: PASS, L4: PASS, L5: PASS
```

## 注意事项

- cpplint 是纯 Python 工具，conanfile.py 不使用 Autotools/CMake
- test_package 使用 VirtualRunEnv 生成器（Conan 2 API）
- package_info() 中 cpp_info.libs 为空（非 C/C++ 库）
- settings = "os", "arch"（不需要 compiler/build_type）
