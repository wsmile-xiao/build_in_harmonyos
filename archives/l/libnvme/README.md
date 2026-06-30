# libnvme

## 简介
libnvme 是 NVMe 存储设备管理库，提供 NVMe 命令和设备管理的 C 语言 API。

## OHOS 适配
- meson 构建（天然避免 config.guess 问题）
- 1.10 版本编译成功

## 依赖
- meson 1.11.1+
- ninja 1.13.1+
- clang 15.0.4+

## 功能验证
```bash
# 检查库
pkg-config --modversion libnvme
pkg-config --modversion libnvme-mi
ls -la $HOME/usr/local/lib/libnvme*.so
```

## 参考
- 主页: https://github.com/linux-nvme/libnvme
- 文档: https://libnvme.readthedocs.io/