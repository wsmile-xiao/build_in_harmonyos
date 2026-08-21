# libubox 20260222

OpenWrt 基础 C 工具库（blob/blobmsg、uloop、ustream、runqueue、kvlist、md5、base64、json_script），
提供 jshn 命令行工具（JSON Shell Notation，用于 shell 脚本中解析/生成 JSON）。

- 构建系统: CMake
- 许可证: ISC
- 上游: https://github.com/openwrt/libubox
- 依赖: json-c/0.18

## 已适配版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 20260222 | published | 2026-08-12 |

## 产物

- 库: libubox.so/.a、libblobmsg_json.so/.a、libjson_script.so
- 命令行工具: bin/jshn
- 头文件: include/libubox/*.h
