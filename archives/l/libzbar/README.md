# libzbar

> 条形码/二维码扫描库

## 简介

libzbar 是一个用于扫描和解码条形码、二维码的开源库。支持多种条码格式包括 QR Code、EAN、UPC、Code128 等。提供 C 库接口和多种语言绑定。

## OHOS 适配要点

- GitHub tarball 未包含 configure 脚本，需运行 autoreconf -fi
- musl libc 缺少 argp.h（GNU扩展），测试套件可能无法运行
- 禁用可选功能（GTK、Qt、Java、Python、ImageMagick）简化编译
- HMDFS 文件系统不支持硬链接

## 排除与替代

无

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| dbus | 1.14.10 | 消息系统 |
| autotools | - | 构建系统 |

## 功能验证

```bash
# 验证库安装
pkg-config --modversion zbar
# 输出: 0.23.93

# 验证工具
zbarcam --help
```

## 参考

- [libzbar GitHub](https://github.com/mchehab/zbar)