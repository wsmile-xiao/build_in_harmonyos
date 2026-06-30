# libident

libident 是一个 IDENT 协议 (RFC 1413) 的 C 语言实现库，提供客户端 API 用于查询远程主机的用户身份。

## 版本信息
- 当前版本: 0.32
- 官网: https://www.remlab.net/files/libident/

## 描述
libident 实现了 IDENT 协议客户端，允许应用程序通过 TCP 端口 113 查询远程连接的用户身份。

主要功能：
- `id_open` / `id_open_addr` — 打开 IDENT 连接
- `id_close` — 关闭 IDENT 连接
- `id_query` — 发送 IDENT 查询
- `id_parse` — 解析 IDENT 响应
- `ident_lookup` — 高级 API：查询文件描述符对应的远程用户
- `ident_id` — 高级 API：返回用户名

## 编译状态
- 鸿蒙难度: 🟢 (低)
- 构建系统: autotools
- 编译器: clang
- 产物: libident.a (静态库) + ident.h (头文件)

## 依赖
- 无外部依赖

## 已知问题
- config.guess (2004年版) 不识别 HarmonyOS，需添加检测分支
- HMDFS umask 077 导致临时文件权限问题，需替换为 umask 022
