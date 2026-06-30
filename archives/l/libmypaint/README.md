# libmypaint

## 简介
libmypaint 是 MyPaint 使用的笔刷引擎库。许多其他绘画程序也使用它。
License: ISC

## OHOS 适配
- autotools 构建
- 1.6.0 版本编译成功
- 需要平台识别补丁（config.guess/config.sub）

## 依赖
- json-c (>= 0.11)
- GLib (可选，用于 GObject-Introspection)
- GObject-Introspection (可选)

## 功能验证
```bash
# 检查库
ls -la $HOME/usr/local/lib/libmypaint*
# 检查 pkg-config
pkg-config --modversion libmypaint
```

## 测试说明
测试执行失败，原因是缺少 GLib 动态库（libgobject-2.0.so.0 和 libglib-2.0.so.0）。
这是运行时依赖问题，不影响库本身的编译和打包。详见 reports/test-report.md。

## 参考
- 主页: https://github.com/mypaint/libmypaint
- 文档: https://github.com/mypaint/libmypaint/wiki