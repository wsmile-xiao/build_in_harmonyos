# protoc-gen-grpc-web 2.1.1 — OpenHarmony 编译记录

## 基本信息
- 软件: protoc-gen-grpc-web
- 版本: 2.1.1
- 构建系统: cmake（自研精简 CMakeLists，规避上游 Bazel）
- 目标: ohos-aarch64
- package_type: application（命令行工具，bin/protoc-gen-grpc-web）

## 编译指导
- 上游 Bazel 构建被规避：插件本体仅一个编译单元 `javascript/net/grpc/web/generator/grpc_generator.cc`，自研 CMakeLists 直接对 `protobuf::libprotoc` imported target 链接
- `Protobuf_DIR`/`utf8_range_DIR`/`absl_DIR` 三个 CMake 变量直指 conan 包内 config 目录（protobuf 33.6.1 为 `cmake_find_mode=none` 的原生 config）
- **禁止手工拼库清单**：protobuf 33 的 utf8 校验拆为 libutf8_range.a/libutf8_validity.a 独立库，手工链接会漏（见 notes.md 问题 2）

## 补丁清单
- `patches/0001-grpc-generator-protobuf-33-absl-string-view-compat.patch`：protobuf 33 兼容（descriptor accessor 返回 absl::string_view 的 51 处编译错误修复），自研，上游 master 无现成修复

## 已知限制
- `--grpc-web_out` 必须带 `mode=grpcweb|grpcwebtext`，否则按设计拒绝生成（上游行为）
- 上游 pin protobuf 29.1，本配方对齐 ohpcd 的 protobuf 33.6.1（需上述兼容补丁）

## 功能验证
- `protoc-gen-grpc-web --version` → `protoc-gen-grpc-web 2.1.1`
- 端到端：`protoc --plugin=protoc-gen-grpc-web=<bin> --grpc-web_out=import_style=commonjs,mode=grpcweb:<dir> sample.proto` 生成 `sample_grpc_web_pb.js`，服务桩/方法桩/import 指令/版本横幅断言 9/9 通过（test_package R34）
