# upb

`upb`（micro protobuf）是 Google Protocol Buffers 的 C 运行时，本适配对应
2020-07-30 的快照 `0.0.0-git200730`。

## 适配要点

- **上游 CMake 不完整**：生成的 `CMakeLists.txt` 从未定义 `descriptor_upb_proto`
  目标（`generated_for_cmake/google/protobuf/descriptor.upb.c` 不参与编译）、
  `cc_test` 被注释掉、且没有任何 `install()` 规则。
- 配方**直接用 OHOS clang 编译 21 个 C 源文件**为 `libupb.a`，并安装公共头
  （`upb/**`、`google/protobuf/descriptor.upb.h`）。
- 无三方依赖；只有 `libc`。

## 上游测试

`./BUILD` 声明 8 个 `cc_test`。其中两个不需要 protoc 生成的 `*.upb.h`，
本配方构建并实跑：

- `tests/pb/test_varint.c`（varint/zigzag 往返，两种解码器）
- `tests/test_table.cc`（hash 表）

其余 6 个要么需要 `protoc` + `protoc-gen-upb`（`upbc/` 需 protobuf+abseil 与
Bazel 工具链），要么需要 Lua 5.2 运行时，本环境不具备，逐条豁免（见
`test_package/MANIFEST.yml`）。

## 消费者测试

`test_package/test_upb.c`：用已安装的 `upb/pb/varint.int.h` 与 `libupb.a`
验证 varint/zigzag/长度辅助函数，共 9 项断言。

## 参考

- 上游：<https://github.com/protocolbuffers/upb>
