# http-prompt 2.1.0 适配笔记

## 编译环境
- 构建系统: Python (setuptools)
- 编译日期: 2026-06-08
- 编译器: Python 3.12
- Python路径: /data/service/hnp/python.org/python_3.12/bin/python3.12
- 状态: built

## 编译步骤

http-prompt 是一个纯 Python 项目，使用 setuptools 构建。

1. **下载源码**：从 GitHub 下载 v2.1.0 tarball
   - URL: https://api.github.com/repos/httpie/http-prompt/tarball/v2.1.0
   - 由于 SSL 证书问题，使用 Python urllib 禁用 SSL 验证下载

2. **初始化编译环境**：ohc-run.py init-build http-prompt 2.1.0 --url=file://...

3. **安装依赖**：使用 pip install 安装到 staging 目录
   - 命令：python3 -m pip install --target=$TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.12/site-packages .
   - 依赖包括：httpie>=2.4.0, click>=5.0, parsimonious>=0.6.2, prompt-toolkit>=1.0.0,<2.0.0, Pygments>=2.1.0, PyYAML>=3.0

4. **制作预编译包**：ohc-run.py package http-prompt 2.1.0
   - 包含所有 Python 依赖
   - 打包为 http-prompt-2.1.0-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载 SSL 证书验证失败 | 鸿蒙系统 SSL 证书配置问题 | 使用 Python urllib 禁用 SSL 验证下载 |
| 2 | pip --root 和 --prefix 不能同时使用 | pip 参数限制 | 使用 --target 参数指定安装路径 |
| 3 | manifest 缺少 build_system 字段 | 模板未正确填写 | 手动添加 build_system: python |

## 源码修改

无补丁，纯 Python 项目直接安装。

## 依赖版本

- httpie: 3.2.4
- click: 8.4.1
- parsimonious: 0.11.0
- prompt-toolkit: 1.0.18
- Pygments: 2.20.0
- PyYAML: 6.0.3
- requests: 2.34.2
- rich: 15.0.0

## 验证结果

```bash
# 设置 PYTHONPATH 指向 staging 目录
export PYTHONPATH=$TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.12/site-packages

# 测试版本
python3 $TEST_PREFIX/$DEFAULT_PREFIX/bin/http-prompt --version
2.1.0

# 测试帮助
python3 $TEST_PREFIX/$DEFAULT_PREFIX/bin/http-prompt --help
Usage: http-prompt [OPTIONS] [URL] [HTTP_OPTIONS]...

Options:
  --spec TEXT  OpenAPI/Swagger specification file.
  --env PATH   Environment file to preload.
  --version    Show the version and exit.
  --help       Show this message and exit.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| http-prompt-2.1.0-ohos-aarch64.tar.gz | 44MB | 预编译包（包含所有依赖） |
| http-prompt-2.1.0-ohos-aarch64-debug.tar.gz | 639KB | 调试符号包 |

## 注意事项

1. http-prompt 是纯 Python 项目，不需要 ELF 签名
2. 预编译包包含所有 Python 依赖，用户安装后可直接使用
3. 需要设置 PYTHONPATH 或将包安装到正确的 site-packages 目录
4. lexer.py 有 SyntaxWarning（无效转义序列），但不影响功能

---

**编译结束**: 2026-06-08 16:43
**最终状态**: built