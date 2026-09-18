# libblobmsg

OpenWrt blobmsg 数据容器库（blob/blobmsg 属性处理与 blobmsg<->json 转换），
切自上游 openwrt/libubox 源码树。

- 构建系统: CMake
- 许可证: ISC
- 上游: https://github.com/openwrt/libubox
- 依赖: json-c/0.18

## 已适配版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2026.02.13 | built | 2026-09-16 |

## 产物

- 库: libubox.so/.a（含 blobmsg 核心）、libblobmsg_json.so/.a、libjson_script.so
- 头文件: include/libubox/blob.h、blobmsg.h、blobmsg_json.h 等
- 无命令行工具（jshn 不随本包发布，纯库类型）
