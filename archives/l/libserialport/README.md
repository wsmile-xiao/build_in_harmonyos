# libserialport

## 简介

libserialport 是一个跨平台的串口访问库，提供统一的 API 来访问串行端口。它是 sigrok 项目的核心依赖库。

## OHOS 适配

### 适配要点

1. **config.guess 修改**: 添加 HarmonyOS 系统识别分支
   - 在 case 语句开头添加 `*:HarmonyOS:*:*` 分支
   - 输出三元组格式：`aarch64-unknown-linux-ohos`

2. **config.sub 修改**: 添加 ohos 平台验证
   - 添加 `ohos-linux` 三元组映射
   - 在 OS 白名单添加 `ohos*`
   - 在 kernel-os 白名单添加 `linux-ohos*`

### 已知问题

- HMDFS 文件系统的临时目录权限限制导致 G0 干净构建验证无法通过
- make check 测试程序编译失败（不影响库功能）

### 与 Linux 差异

无显著差异，纯 C 库，无需特殊处理。

## 依赖

无外部依赖，标准 C 库即可编译。

## 功能验证

```bash
# 验证库文件
ls -la $PREFIX/lib/libserialport*
# 验证头文件
ls -la $PREFIX/include/libserialport.h
# pkg-config 验证
pkg-config --modversion libserialport
```

## 编译产物

| 文件 | 说明 |
|------|------|
| libserialport.a | 静态库 |
| libserialport.so.0.1.1 | 动态库 |
| libserialport.h | 头文件 |
| libserialport.pc | pkg-config 文件 |

## 参考

- 官网: https://sigrok.org/wiki/Libserialport
- 源码: https://github.com/sigrokproject/libserialport
- 许可证: LGPL-3.0-or-later