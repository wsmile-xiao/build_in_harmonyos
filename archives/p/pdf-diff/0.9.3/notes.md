# pdf-diff 0.9.3 适配笔记

## 编译环境
- 构建系统: custom (Python setuptools)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- Python版本: 3.12.8
- 状态: built

## 编译步骤

1. 使用 PyPI 源码包下载 (GitHub URL 404)
2. 安装依赖: fast-diff-match-patch (pip install)
3. DESTDIR模式编译: `python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX`
4. 直接安装到 $DEFAULT_PREFIX: `python3 setup.py install --prefix=$DEFAULT_PREFIX`
5. 创建 .pth 文件确保 Python 搜索路径包含 $DEFAULT_PREFIX/lib/python3.12/site-packages

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub URL 404 | v0.9.3 tag不存在或命名不同 | 使用 PyPI 源码包URL替代 |
| 2 | pip install --prefix+--root 报错 | pip不能同时设置--home和--prefix | 使用 setup.py install 替代 pip |
| 3 | pip --root安装到临时target目录 | pip --root 使用pip内部target路径 | 使用 setup.py install --prefix --root |
| 4 | pdf-diff命令找不到package metadata | $DEFAULT_PREFIX不在Python sys.path | 创建.pth文件添加搜索路径 |
| 5 | Pillow import失败(Permission denied) | pip-global中的Pillow缺少ELF签名 | 系统site-packages中的Pillow可用，环境需配置优先使用系统版本 |

## 依赖版本

- Python: 3.12.8
- fast-diff-match-patch: 2.1.0
- lxml: 5.3.0
- Pillow: 12.2.0 (pip-global) / 11.0.0 (system site-packages)
- setuptools: 82.0.1
- pdftotext: 已安装但运行时链接问题(poppler)

## 验证结果

```bash
# 模块导入验证
python3 -c "import pdf_diff; print('pdf_diff module imported successfully')"
# 输出: pdf_diff module imported successfully

# Staging 验证
STAGING_PREFIX=$TEST_PREFIX/$DEFAULT_PREFIX
二进制: 1 (bin/pdf-diff), 库文件: 11
# PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/pdf-diff | 命令行入口脚本 |
| lib/python3.12/site-packages/pdf_diff/ | Python模块 |

## 注意事项

- pdf-diff是纯Python包，无需C编译，DESTDIR模式需适配Python安装方式
- 运行时依赖pdftotext(poppler)和Pillow，需确保系统优先加载已签名的Pillow
---

**编译结束**: 2026-05-28 11:24
**最终状态**: built
