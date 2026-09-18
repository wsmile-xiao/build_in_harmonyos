# libgadu — OpenHarmony 编译档案

## 软件简介
libgadu 是 Gadu-Gadu 即时通讯协议的客户端 C 库（LGPL-2.1-only），上游 https://github.com/wojtekka/libgadu（已归档，只读）。

## 功能概述
- Gadu-Gadu 协议编解码、消息组装与解析
- 字符编码转换（gg_encoding_convert）
- 哈希与数据包处理（hash/packet）
- 可选 TLS（gnutls）与 protobuf-hub 支持

## OHOS 适配要点
- 最小离线移植：`--without-gnutls --without-protobuf --without-pthread`（三者上游均为可选），核心协议、编码、消息、哈希、包解析不受影响
- pthread 保持自动探测改为上游 --without-pthread 关闭（OHOS lld 未解析 pthread_setcancelstate/pthread_cancel）
- 2017 版 config.guess 不识别 HarmonyOS，固定 `--build=aarch64-unknown-linux-gnu` 跳过猜测（bash 5.3 同款做法），仍为原生构建
- 上游测试 `make check`（test/automatic，共 9 项）在 build() 内真实运行并解析 TOTAL/PASS/FAIL/SKIP

## 依赖关系
- 无外部依赖（零依赖离线移植）

## 参考资料
- [libgadu 官网](https://libgadu.github.io/)
- [上游仓库（已归档）](https://github.com/wojtekka/libgadu)
