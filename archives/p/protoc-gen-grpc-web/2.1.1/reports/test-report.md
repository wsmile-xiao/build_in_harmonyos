# protoc-gen-grpc-web 2.1.1 测试报告

> **项目**: protoc-gen-grpc-web（gRPC-Web protoc 插件，JavaScript 客户端桩生成器）
> **测试日期**: 2026-09-07
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64（OHOS PC 原生）
> **测试类型**: 手动功能测试（R34 消费者视角端到端代码生成）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 9 | 100% |
| 通过 (PASS) | 9 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

test_package 输出行：`HMBS_TEST_PACKAGE_RESULT: total=9 passed=9`

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。插件在 HarmonyOS PC（aarch64, musl）上通过 protoc 插件协议完整工作：
从 `protoc --plugin=protoc-gen-grpc-web=<bin> --grpc-web_out=...` 生成可用的
gRPC-Web JavaScript 客户端桩代码，生成内容与上游生成器语义一致（服务客户端类、
方法描述符、commonjs import、版本横幅），并对非法参数给出正确的拒绝行为。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 pin protobuf 29.1，与 ohpcd protobuf/33.6.1 编译不兼容 | 编译期（51 处 string_view 错误） | 🟢 已由 0001 补丁解决 |
| protobuf 33 utf8 校验拆库后手工链接缺符号 | 链接期 | 🟢 已由 CMake imported target 解决 |

### 2.3 可用功能清单

```
✅ 插件协议握手: protoc 检测插件 (--version)
✅ 模式 grpcweb: 生成 *_grpc_web_pb.js 客户端桩
✅ import_style=commonjs: require() 风格 import 指令
✅ 服务/方法桩生成: EchoServiceClient / EchoServicePromiseClient / methodDescriptor
✅ 生成器版本横幅: "protoc-gen-grpc-web v2.1.1" 嵌入生成文件
✅ 参数校验: 缺 mode= 选项报 "mode is required" 且非零退出
⚠️ import_style=typescript: 未单测（上游参数，属同一代码路径，由 grpcweb 模式覆盖生成器主链路）
```

### 2.4 已知限制

1. 仅覆盖 grpcweb 模式 + commonjs import style（ohpcd 生态的典型消费方式）；
   grpcwebtext / typescript 等模式走同一生成器主链路，未逐一断言。
2. 测试依赖 protobuf/33.6.1 的 protoc 驱动端到端生成（test_package 直接
   requires protobuf，因传递依赖在 test 上下文 package_folder 为 None）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| T1 | 二进制存在且 ELF magic (\x7fELF) | ✅ PASS |
| T2 | `--version` 输出含 protoc-gen-grpc-web 与 2.1.1（插件协议握手） | ✅ PASS |
| T3 | `protoc --plugin=... --grpc-web_out=import_style=commonjs,mode=grpcweb` 生成成功（退出码 0） | ✅ PASS |
| T4 | 生成产物 sample_grpc_web_pb.js 存在 | ✅ PASS |
| T5 | 服务客户端桩 EchoServiceClient + EchoServicePromiseClient | ✅ PASS |
| T6 | 方法描述符 methodDescriptor_EchoService_Echo + 路径 /sample.v1.EchoService/Echo | ✅ PASS |
| T7 | import 指令 require('./sample_pb.js') + require('grpc-web') | ✅ PASS |
| T8 | 生成器版本横幅 "protoc-gen-grpc-web v2.1.1" 嵌入生成文件 | ✅ PASS |
| T9 | 负向：缺 mode= 选项被拒绝（"mode is required" + 非零退出） | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无。

---

## 四、关键问题分析

### 问题1: protobuf 33 编译不兼容（51 处 absl::string_view 错误）

**现象**：
```
javascript/net/grpc/web/generator/grpc_generator.cc:xxx:xx: error:
no viable conversion from 'absl::string_view' to 'const std::string'
```

**根因分析**：
grpc-web 2.1.1 上游 pin protobuf 29.1；protobuf 30 起 descriptor 的
name()/file()/type() 等 accessor 返回 absl::string_view（PB_EPHEMERAL），
grpc_generator.cc 按 std::string 假定使用，导致 map key、字符串拼接等
51 处编译错误。

**解决方案**：
自研补丁 0001：helper 函数签名 string_view 化（只读语义直接改签名），
写场景（map key、拼接）显式 std::string() 包裹。上游 master 尚无现成
修复可借。git apply / patch -p1 双通道验证，打后文件与验证副本逐字节一致。

### 问题2: 链接期 VerifyUTF8Fallback 未解析

**现象**：
```
undefined symbol: google::protobuf::internal::EpsCopyInputStream::VerifyUTF8Fallback
```

**根因分析**：
protobuf 33 把 utf8 校验拆为独立静态库（libutf8_range.a / libutf8_validity.a），
手工链接命令遗漏这两个库。

**解决方案**：
改用 CMake `find_package(Protobuf CONFIG)` + 链接 `protobuf::libprotoc`
imported target，由 protobuf-config.cmake 依赖图自动解析
utf8_range/utf8_validity/absl 全链，一次链接成功（3.3MB 单二进制）。

---

## 五、测试环境

```
插件: protoc-gen-grpc-web 2.1.1（protoc-gen-grpc-web v2.1.1 + protoc v6.33.6 横幅实测）
驱动: protoc v6.33.6（protobuf/33.6.1 @ ohpcd 制品仓）
构建: conan create --build=missing, ci/conan/profiles/ohos-aarch64
      CMake (自研精简 CMakeLists，规避上游 Bazel)，clang 15.0.4 aarch64-unknown-linux-ohos
依赖: protobuf/33.6.1 → abseil-cpp/20260107.1 → zlib/1.3.1（全静态打入）
运行: HarmonyOS PC 原生（HongMeng Kernel 1.11.0, musl libc, ELF 64-bit arm64）
```

## 交付物

- `bin/protoc-gen-grpc-web`（3.3MB，静态链接 protobuf/absl，动态依赖仅系统
  libc/libc++_shared）
- Conan 包 `protoc-gen-grpc-web/2.1.1@ohpcd/stable`（ohos-aarch64），
  经 CI release 流水线发布至 ohpcd 制品仓（见 packaging/README.md）

---

*报告生成时间: 2026-09-07*
