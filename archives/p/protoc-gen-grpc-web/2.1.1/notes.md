# protoc-gen-grpc-web 2.1.1 适配笔记

## 软件背景

- **上游**：grpc/grpc-web 2.1.1（gRPC for Web Clients）
- **官方源码**：https://github.com/grpc/grpc-web/archive/refs/tags/2.1.1.tar.gz
- **sha256**：`7766763275c6bf99115c9b535aaa3c507566847d47ea72a1f70da7fe427a98d3`（codeload 二次验证一致）
- **产物**：单二进制 protoc 插件 `protoc-gen-grpc-web`，为 protoc 生成 JavaScript gRPC-Web 客户端桩代码
- **package_type**: `application`（命令行工具，无库产物）

## 依赖

- 唯一硬依赖 `protobuf/33.6.1`（ohpcd 已发布，recipe revision `335973ed...`，本机 conan 缓存含 `lib/libprotoc.a`、`include/google/protobuf/compiler/plugin.h`、`bin/protoc` 可运行；传递依赖 abseil-cpp/20260107.1 + zlib/1.3.1）
- 不需要 grpc 核心（插件只用 libprotoc 的 CodeGenerator API，不走网络）

## 构建方式：Bazel 规避（重要）

上游用 **Bazel** 构建（`javascript/net/grpc/web/generator/BUILD.bazel`、`MODULE.bazel`），CI 能力矩阵无 Bazel。规避方式：

1. 上游插件本体只是**单个源文件** `javascript/net/grpc/web/generator/grpc_generator.cc`（约 1500 行，无其他编译单元依赖）
2. 自研精简 `CMakeLists.txt`（随配方 exports_sources）只编译该文件
3. 链接 `protobuf::libprotoc` imported target —— protobuf 33.6.1 包保留了上游 component-rich CMake config（`cmake_find_mode=none`），通过 `Protobuf_DIR`/`utf8_range_DIR`/`absl_DIR` 三个变量直指包内 config 目录（与 protobuf/33.6.1 配方 test_package 同款做法）

## 关键问题 1：protobuf 33 string_view 迁移（编译期，51 处错误）

**现象**：grpc-web 2.1.1 上游 pin `protobuf 29.1`，而 ohpcd 制品仓只有 protobuf 33.6.1。protobuf 30+（`v30.0` 起）将 descriptor accessor（`name()`/`full_name()`/`package()`/`json_name()`/`filename()` 等）返回值从 `const std::string&` 改为 `absl::string_view`，原代码按 `std::string` 使用产生 **51 处编译错误**，典型三类：

1. `std::map<string, string>` 插入时 key/value 需要 `std::string`：`no matching function for call to 'std::map<...>::insert(std::pair<absl::string_view, absl::string_view>)'`
2. `string + string_view` 拼接二义性：`no match for 'operator+'`
3. helper 函数形参声明 `string`，传入 accessor 返回的 `string_view` 报转换错误

**补丁方案**（自研 `patches/0001-grpc-generator-protobuf-33-absl-string_view-compat.patch`，68 insertions / 57 deletions）：

- helper 函数签名 `string_view` 化：`string LowercaseFirstLetter(string s)` → `string LowercaseFirstLetter(absl::string_view s)` 等（这些 helper 只读入参，返回值仍为 `std::string`，安全）
- map key/字符串拼接处显式 `std::string(...)` 包裹 accessor 返回值
- 头部增加 `#include "absl/strings/string_view.h"`

**自研理由**：上游 master 的 `grpc_generator.cc` 截至 2026-09 无对应修复可借用（master 分支该文件与 2.1.1 tag 在这些调用点同构，无 string_view 化改动；上游通过 MODULE.bazel 锁 protobuf 29.x 而非改代码）。补丁由两轮幂等替换脚本（apply_patch.py + apply_patch3.py）对上游源文件生成，再以 `git diff` 固化为规范 patch；`git diff --check` 零空白告警，`git apply --check` 与 GNU `patch -p1 --dry-run` 双通道验证通过，打补丁后文件与已验证编译零错误的工作副本逐字节一致。

**知识图谱查询**：`engine "cannot convert absl::string_view to std::string descriptor->name() protobuf"` → **未命中**（新错误模式，已沉淀知识草稿，见下）。

## 关键问题 2：protobuf 33 utf8 校验库拆分（链接期）

**现象**：手工链接命令（`clang++ grpc_generator.o libprotoc.a libprotobuf.a <absl...>`）报未解析符号 `google::protobuf::internal::EpsCopyInputStream::VerifyUTF8Fallback`。

**根因**：protobuf 33 把 utf8 校验拆成独立静态库 `libutf8_range.a` + `libutf8_validity.a`，且 `libprotobuf.a` 的 pkg-config/链接清单只在 CMake target 链上表达（`protobuf::libprotobuf` 的 `INTERFACE_LINK_LIBRARIES` 含 `utf8_range::utf8_validity` → `utf8_range::utf8_range`），手工拼库清单容易遗漏。

**解法**：改用 CMake `find_package(Protobuf CONFIG REQUIRED)` + `target_link_libraries(protoc-gen-grpc-web PRIVATE protobuf::libprotoc)`，conan 依赖图自动解析 utf8_range/utf8_validity/absl 全链。**不要**手工拼库清单。

**知识图谱查询**：`engine "undefined reference ... VerifyUTF8Fallback"` → 命中 **E014**，但判定为**误匹配**：E014 根因是"鸿蒙内核未实现 POSIX 系统调用/musl 未导出符号（syslog/getrandom）"，与本题"protobuf 33 静态库拆分导致链接清单缺失"根因不同，E014 的 -D 宏禁用方案不适用。真实解法已沉淀知识草稿。

## 端到端验证（R34）

测试链：`protoc(protobuf/33.6.1 bin) --plugin=protoc-gen-grpc-web=<本包 bin> --grpc-web_out=import_style=commonjs,mode=grpcweb:<dir>`，sample.proto 定义 `service EchoService { rpc Echo(EchoRequest) returns (EchoResponse); }`，9 项断言：

- T1 插件二进制 ELF 魔数
- T2 `--version` 冒烟（输出含 `protoc-gen-grpc-web 2.1.1`）
- T3 protoc+插件端到端生成成功
- T4 生成 `sample_grpc_web_pb.js` 存在
- T5 服务桩 `EchoServiceClient`/`EchoServicePromiseClient`
- T6 方法桩 `methodDescriptor_EchoService_Echo` + RPC 路径 `/sample.v1.EchoService/Echo`
- T7 import 指令 `require('./sample_pb.js')` + `require('grpc-web')`
- T8 生成文件头部版本横幅 `protoc-gen-grpc-web v2.1.1`
- T9 负向：缺 `mode=` 参数被拒绝（`mode is required` + 非零退出）

本地实测 9/9 通过；生成文件头部同时确认 `protoc v6.33.6`（由 protobuf 33.6.1 的 protoc 驱动）。

## 其他备忘

- 本机构建即 OHOS PC 原生 aarch64（非交叉），profile `ci/conan/profiles/ohos-aarch64`，clang++ 15 / libc++ / cppstd=17
- `--grpc-web_out` 必须带 `mode=grpcweb`（或 grpcwebtext），否则插件按设计报 `options: mode is required` 拒绝生成（上游行为，非缺陷）
- 知识草稿：protobuf 33 string_view 迁移 + utf8 库拆分两条错误模式（match_keywords/root_cause/rec_approach 实填），提交于 knowledge/drafts/
---

**编译结束**: 2026-09-07 11:57
**最终状态**: published
