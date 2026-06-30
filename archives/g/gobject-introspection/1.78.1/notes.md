# gobject-introspection 1.78.1 适配笔记

## 编译环境
- 构建系统: meson+ninja
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4
- 状态: built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python 3.12 distutils.msvccompiler 移除 | Python 3.12 弃用 distutils | 添加 try/except 导入 _msvccompiler |
| 2 | Python 扩展模块无法加载 | HMDFS + SELinux ELF 签名限制 | 禁用 introspection 数据生成 |

## 源码修改

修改 giscanner/ccompiler.py，添加 Python 3.12 兼容性：
```python
try:
    from distutils.msvccompiler import MSVCCompiler
except ImportError:
    from distutils._msvccompiler import MSVCCompiler
```

## 平台限制

1. Python 扩展模块无法加载（E107）
2. introspection 数据生成功能已禁用
3. 运行时需设置 LD_LIBRARY_PATH

---
**编译结束**: 2026-05-26
**最终状态**: built
