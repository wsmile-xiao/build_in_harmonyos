## PR 信息
- **三方库名称**：protoc-gen-grpc-web（gRPC for Web Clients — gRPC-Web protoc 插件，为 protoc 生成 JavaScript gRPC-Web 客户端桩代码）
- **上游版本**：2.1.1
- **上游仓库地址**：https://github.com/grpc/grpc-web/archive/refs/tags/2.1.1.tar.gz（sha256: 7766763275c6bf99115c9b535aaa3c507566847d47ea72a1f70da7fe427a98d3）
- **适配路径**：路径 A（基础适配 + 1 个兼容补丁；上游 Bazel 构建规避为自研精简 CMake）
- **使用知识库**：E017（镜像注入预防，审计中拦截一次回滚残留污染并修复）；新增草稿 E543（protobuf 30+ descriptor accessor 返回 absl::string_view 的下游迁移）、E544（protobuf 33 utf8 校验库拆分导致手工链接缺符号）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 集成测试 | 0 | 上游测试体系为 Bazel + Karma/mocha 浏览器端 JS 单测（javascript/net/grpc/web/），依赖 Node/浏览器运行时，不含可在本机原生执行的服务端用例 |
| 单元测试 | 0 | 插件生成器本体（grpc_generator.cc）在上游构建中无独立单测 |
| **合计** | **0** | 上游无可移植原生测试 |

### 是否存在对上游测试用例的修改？
否（补丁仅修改 grpc_generator.cc 的 descriptor accessor 兼容性调用，不触及任何测试文件）

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 集成测试 | 1 | 新增 | test_package 以消费者视角驱动 protoc --plugin 端到端生成（R34） |
| 单元测试 | 9 项断言 | 新增 | 生成内容实质断言（非冒烟），全部通过 |
| **合计** | **1 套 + 9 断言** | | HMBS_TEST_PACKAGE_RESULT: total=9 passed=9 |

### 补全测试用例说明
是。test_package 补全范围（conan test 实测全过）：
1. **二进制健全性**（1 项）：ELF magic 校验（\x7fELF）
2. **插件协议握手**（1 项）：`--version` 输出含 protoc-gen-grpc-web 与 2.1.1
3. **端到端代码生成**（3 项）：`protoc --plugin=protoc-gen-grpc-web=<bin> --grpc-web_out=import_style=commonjs,mode=grpcweb` 生成 sample_grpc_web_pb.js；断言产物存在 + 生成进程退出码 0
4. **生成内容实质断言**（4 项）：服务客户端桩（EchoServiceClient/PromiseClient）、方法描述符（methodDescriptor_EchoService_Echo + /sample.v1.EchoService/Echo 路径）、commonjs import 指令（require('./sample_pb.js') + require('grpc-web')）、生成器版本横幅（protoc-gen-grpc-web v2.1.1）
5. **负向测试**（1 项）：缺 mode= 选项被拒绝（"mode is required" + 非零退出码）
6. **清理卫生**（R34）：try/finally 清理生成产物，不残留

---

## 上游测试用例修改说明
未修改。0001 补丁只移植 grpc_generator.cc 对 protobuf 33 的兼容调用（helper 签名 string_view 化 + 拼接点 std::string() 包裹），不改变生成器逻辑与输出语义。

## 验证结果

### 编译验证
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS 原生工具链)
- 编译状态: 成功（单编译单元 grpc_generator.cc，0 error）
- 构建系统: CMake（上游 Bazel 规避——CI 无 Bazel 工具链；插件本体为单翻译单元，自研精简 CMakeLists 直接编译并链接 protobuf::libprotoc imported target）
- 配置选项: find_package(Protobuf CONFIG REQUIRED)，tc.variables 指定 Protobuf_DIR/utf8_range_DIR/absl_DIR（protobuf/33.6.1 配方同款先例）
- 编译 flags: profile 默认（-O2 -std=c++17，check_min_cppstd 17）

### 产物验证
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 编译无错误 | PASS | conan-verify G2 干净构建（四次全过） |
| 产物存在性 | PASS | bin/protoc-gen-grpc-web（3.3MB） |
| ELF 格式 | PASS | ELF 64-bit arm64，动态链接 musl，仅依赖系统 libc/libc++_shared |
| 运行测试 | PASS | test_package 9 断言全过 + 插件协议握手实测 |
| 动态依赖 | PASS | protobuf/absl/zlib 全部静态打入 |

### 补丁说明
| 补丁 | 内容 | 验证 |
|------|------|------|
| 0001-grpc-generator-protobuf-33-absl-string-view-compat.patch | protobuf 33 兼容：helper 函数签名 absl::string_view 化 + map key/字符串拼接显式 std::string() 包裹 + 补 include（68+/57-） | git apply --check 与 GNU patch -p1 双通道通过；打补丁后文件与逐字节编译验证副本一致 |

自研理由：上游 master 同文件无 string_view 化修复可借（上游通过 MODULE.bazel 锁 protobuf 29.x 规避而非改代码）。

### 依赖
- protobuf/33.6.1（ohpcd 已发布，唯一硬依赖）
- abseil-cpp/20260107.1（protobuf 传递依赖）
- zlib/1.3.1（protobuf 传递依赖）

### 测试结论
- 总体评价: 通过（conan-verify G0-G4 + L2/L4/L5 四次全 PASS + W3 本地 CI 模拟通过 + W4 审计 verdict=pass P0=0 P1=0）
- 已知限制: 端到端断言覆盖 grpcweb 模式 + commonjs import style（ohpcd 生态典型消费方式）；grpcwebtext/typescript 模式走同一生成器主链路，未逐一断言

### 遇到的问题与解决方案
| 问题 | 解决方案 |
|------|----------|
| 上游 pin protobuf 29.1，protobuf 33 descriptor accessor 返回 absl::string_view → 51 处编译错误 | 自研 0001 补丁：只读 helper 签名 string_view 化，写场景 std::string() 包裹（知识草稿 E543） |
| 链接期 VerifyUTF8Fallback 未解析（protobuf 33 拆出 libutf8_range/libutf8_validity） | 链接 protobuf::libprotoc imported target，依赖图自动解析 utf8_range/validity/absl 全链（知识草稿 E544） |
| CI 无 Bazel 工具链 | 插件为单翻译单元，自研精简 CMakeLists 规避整个 Bazel 构建 |
| test_package 中 protobuf 传递依赖 package_folder=None，拿不到 protoc | test_package 直接 requires protobuf/33.6.1 |
| 插件生成模式必填参数缺失报 "mode is required" | 测试命令显式 mode=grpcweb；同时固化为负向测试断言 |
| E017 镜像注入回滚机制一次残留污染 conandata.yml | W4 审计发现，恢复官方 URL 后 amend，conan-verify 复验全绿 |

### 验证命令
```bash
# conan-verify G0-G4（干净构建 + test_package + 门禁）
python3 scripts/ohc-run.py conan-verify protoc-gen-grpc-web 2.1.1
# → Verdict: PASS（G2 干净构建 + test_package 9 断言全过）

# 消费者视角快速复验
conan test test_package protoc-gen-grpc-web/2.1.1@ohpcd/stable -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
# → HMBS_TEST_PACKAGE_RESULT: total=9 passed=9

# 端到端冒烟（与 test_package 同款链路）
protoc --plugin=protoc-gen-grpc-web=<pkg>/bin/protoc-gen-grpc-web \
  --grpc-web_out=import_style=commonjs,mode=grpcweb:out sample.proto
# → out/sample_grpc_web_pb.js 含 EchoServiceClient 桩 + v2.1.1 横幅
```

---

## 补充说明

### Bazel 规避说明
grpc-web 上游用 Bazel 构建（javascript/net/grpc/web/generator/BUILD.bazel），CI 能力矩阵无 Bazel。插件本体仅一个源文件（约 1500 行，无其他编译单元依赖），自研 CMakeLists（随配方 exports_sources）只编译 grpc_generator.cc 并链接 protobuf::libprotoc，产物与上游语义一致（生成器代码除兼容补丁外零改动）。

### protobuf 33 兼容性说明
ohpcd 制品仓的 protobuf 为 33.6.1（grpc-web 2.1.1 上游锁 29.1）。protobuf 30+ 将 descriptor accessor 返回 absl::string_view，33 又将 utf8 校验拆为独立库。本适配通过 0001 补丁 + imported target 链接完成迁移，经验沉淀知识草稿 E543/E544（string_view 迁移模式与 utf8 库拆分链接模式，可复用于其它 pin 旧版 protobuf 的 protoc 插件）。

### 产物形态（application，R38）
纯可执行包：`bin/protoc-gen-grpc-web`（3.3MB ELF arm64 musl 动态链接，protobuf/absl/zlib 全静态打入，仅依赖系统 libc/libc++_shared）。软件级 commands.json 已声明（type=tool，binary=true）。
