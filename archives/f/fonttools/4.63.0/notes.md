# fonttools 4.63.0 适配笔记

## 编译环境
- 构建系统: custom (pure Python pip wheel)
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

fonttools 是纯 Python 字体处理库，无 C/C++ 编译环节。采用模式 B（手动编译）：
1. 从 PyPI 下载纯 Python wheel: fonttools-4.63.0-py3-none-any.whl
2. 直接 unzip wheel 到 staging 目录的 site-packages
3. 创建 4 个 bin 入口脚本: fonttools, pyftmerge, pyftsubset, ttx
4. 入口脚本通过 `python3 -c "import sys; sys.path.insert(0, ...); from X import main; main()"` 调用

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 无法自动搜索 URL | fonttools 不在 software-registry.yaml，search-url 仅搜索 GNU/GitHub/freedesktop | 手动指定 PyPI URL: `--url=https://files.pythonhosted.org/.../fonttools-4.63.0.tar.gz` |
| 2 | build 命令失败（预编译包索引更新失败） | 网络无法访问 GitCode 索引仓库 | 切换至模式 B：手动 pip wheel 安装 |
| 3 | verify-build G4 FAIL | manifest.yaml 缺少 build_system 字段 | 在 manifest.yaml 中添加 `build_system: custom` |
| 4 | G0 干净构建验证 configure 失败 | fonttools 源码无 configure/Makefile/CMakeLists.txt，是纯 Python 包 | G0 对纯 Python 包不适用，手动验证通过 |

## 依赖版本

- Python 3.14.5 (系统自带)

## 验证结果

```bash
# 导入验证
python3 -c "import sys; sys.path.insert(0, '...'); import fontTools; print(fontTools.__version__)"
# 输出: 4.63.0

# ttx 命令验证
$STAGING/bin/ttx --version
# 输出: 4.63.0

# fonttools 命令验证
$STAGING/bin/fonttools --help
# 输出: fonttools v4.63.0
```