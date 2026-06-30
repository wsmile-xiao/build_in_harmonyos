# E107: 鸿蒙系统 ELF 签名导致 Python 扩展模块无法加载

## 错误特征

```
ImportError: Error loading shared library ... Permission denied
```

## 根因

鸿蒙系统要求 ELF 文件签名才能执行。HMDFS + SELinux 安全限制导致 Python 无法加载自定义编译的扩展模块。

## 解决方案

禁用需要加载 Python 扩展模块的功能：
- meson: `-Dbuild_introspection_data=false`
- autotools: `--disable-introspection`

## 适用范围

所有包含 Python 扩展模块的软件。

## 平台限制

这是鸿蒙系统的已知限制，无法完全解决。
