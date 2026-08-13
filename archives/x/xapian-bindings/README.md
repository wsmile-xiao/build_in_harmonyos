# Xapian Bindings

## 简介

xapian-bindings 是 Xapian 搜索引擎核心库的 Python 绑定，提供 `import xapian` 的
Python API（SWIG 生成的 C++ 扩展模块）。

## 基本信息

- **软件名称**: xapian-bindings
- **显示名**: Xapian Bindings
- **描述**: Xapian 搜索引擎的 Python 绑定
- **分类**: library (python-require)
- **官网**: https://xapian.org/
- **许可证**: GPL-2.0-or-later
- **构建系统**: autotools (configure + make, python3 绑定)

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.4.26 | built | 2026-08-10 |

## OHOS 适配说明

- 从 xapian-bindings 1.4.26 源码构建 python3 绑定
  （tarball 已预生成 xapian_wrap.cc，无需 swig）
- 依赖 xapian-core/1.4.26（制品仓 ohpcd 已发布）
- 补丁 0001-configure.patch: E011 umask 077→022（HMDFS 权限）
- 链接: libc++（OHOS SDK 无 libstdc++）+ 显式 libpython3.12
- 产物安装到 python site-packages（lib/python3.12/site-packages/xapian）
