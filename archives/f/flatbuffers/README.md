# FlatBuffers

## 简介
FlatBuffers 是 Google 开发的高效跨平台序列化库，专为游戏和其他性能敏感应用设计。

**核心优势**：
- 比 Protocol Buffers 更快（无需解析步骤）
- 直接访问序列化数据，无需解包
- 内存占用小，适合移动设备
- 支持多种语言（C++, Java, C#, Go, Python, JavaScript 等）

## 主要组件
- `flatc`: FlatBuffers 编译器，将 schema 编译为目标语言代码
- `libflatbuffers.a`: C++ 静态库
- `include/flatbuffers/`: 头文件（header-only 可选）

## 使用场景
- 游戏数据存储和传输
- 移动应用数据序列化
- 高性能 RPC 协议
- 嵌入式系统数据存储

## 参考资料
- 官网：https://google.github.io/flatbuffers/
- GitHub：https://github.com/google/flatbuffers
- 文档：https://google.github.io/flatbuffers/flatbuffers_guide.html