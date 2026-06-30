# libks

**描述**: SignalWire libks - C utility library for SignalWire products

**版本**: 2.0.11

**状态**: built

**依赖**: openssl, uuid

**许可证**: MIT

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libks 2.0.11
```

## 鸿蒙适配说明

- libm 集成在 libc 中，不需要单独链接
- libatomic 不存在，原子操作已内置
- 需要修复 OpenSSL pkg-config 文件的路径