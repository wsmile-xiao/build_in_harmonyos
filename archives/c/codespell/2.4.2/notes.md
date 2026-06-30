# codespell 2.4.2 适配笔记

## 编译环境
- 构建系统: python
- 编译日期: 2026-06-08
- 编译器: N/A（Python 项目）
- 状态: built

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 scripts/ohc-run.py init-build codespell 2.4.2 --url=file:///storage/Users/currentUser/tmp/codespell-2.4.2.tar.gz
   ```

2. **下载源码**
   - 从 GitHub 下载 tarball：https://api.github.com/repos/codespell-project/codespell/tarball/v2.4.2
   - 使用 curl -k 忽略 SSL 证书验证（鸿蒙系统证书链不完整）

3. **构建 wheel 包**
   - 设置环境变量解决 setuptools-scm 版本检测问题：
     ```bash
     export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_codespell=2.4.2
     ```
   - 使用 pip 构建 wheel 包：
     ```bash
     python3 -m pip install --root=$TEST_PREFIX .
     ```

4. **手动安装到 staging 目录**
   - 从 PyPI 下载官方 wheel 包
   - 解压到正确的 Python 包目录：
     ```bash
     unzip codespell-2.4.2-py3-none-any.whl
     ```
   - 创建可执行脚本：
     ```bash
     cat > $DEFAULT_PREFIX/bin/codespell << 'EOF'
     #!/data/service/hnp/python.org/python_3.12/bin/python3.12
     import sys
     from codespell_lib import _script_main
     sys.exit(_script_main())
     EOF
     ```

5. **验证和打包**
   - 验证构建：`python3 scripts/ohc-run.py verify-build codespell 2.4.2`
   - 打包：`python3 scripts/ohc-run.py package codespell 2.4.2`
   - 完成：`python3 scripts/ohc-run.py finish codespell 2.4.2 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙系统证书链不完整 | 使用 curl -k 忽略 SSL 验证 |
| 2 | setuptools-scm 版本检测失败 | GitHub tarball 缺少 .git 目录 | 设置 SETUPTOOLS_SCM_PRETEND_VERSION_FOR_codespell=2.4.2 |
| 3 | make install 无目标 | Python 项目无传统 Makefile | 使用 pip 安装 wheel 包 |
| 4 | pip --root 路径问题 | DESTDIR 模式不适用于 Python | 手动解压 wheel 包到正确路径 |
| 5 | 质量门禁缺少 build_system | manifest.yaml 字段名错误 | 更新为 build_system: python |

## 源码修改

无补丁文件，直接使用官方 wheel 包。

## 依赖版本

- Python 3.12.8
- pip 24.3.1
- setuptools（系统自带）

## 验证结果

```bash
$ codespell --version
2.4.2

$ codespell --help
usage: codespell [-h] [--version] [-d] [-c] [-w] ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| codespell-2.4.2-ohos-aarch64.tar.gz | 1.7M | 预编译包 |

## 注意事项

1. **Python 包的特殊性**：codespell 是纯 Python 包，不涉及 ELF 二进制签名
2. **setuptools-scm 限制**：从 GitHub 下载的 tarball 缺少版本元数据，需要手动指定版本
3. **pip 安装方式**：Python 包不适用传统的 configure/make/DESTDIR 流程
4. **质量门禁调整**：Python 包的验证需要更新 manifest.yaml 的 build_system 字段

---
**编译结束**: 2026-06-08 22:20
**最终状态**: built