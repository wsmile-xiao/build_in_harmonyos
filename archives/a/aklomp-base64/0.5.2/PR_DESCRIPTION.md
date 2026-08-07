- **三方库名称**：aklomp-base64
- **上游版本**：0.5.2
- **上游仓库地址**：https://github.com/aklomp/base64
- **适配路径**：路径 A（基础适配）
- **使用知识库**：纯 C99 libc-only，Makefile 一键构建（make lib/libbase64.o），无需 configure

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | test/test_base64.c（编解码正确性，含各 SIMD codec 检测） |
| 性能基准 | 1 | test/benchmark.c（编解码吞吐量基准） |
| **合计** | **2** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 不变 | test_base64.c 已在 OHOS 真机编译并运行 |
| 性能基准 | 1 | 不变 | benchmark.c 已在 OHOS 真机编译并运行 |
| 消费者测试 | 1 | +1 | 链接 libbase64.a，encode/decode 往返一致验证 |
| **合计** | **3** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游已有 test_base64.c 单元测试与 benchmark 基准，适配后补充了消费者测试

> - **补全的测试范围**：新增 1 个消费者测试（test.c：base64_encode "Hello, World!" 得 SGVsbG8sIFdvcmxkIQ==，再 decode 往返一致）
> - **补全原因**：验证 libbase64.a 在 OHOS 上可链接可用
> - **新增测试文件清单**：
>   1. `archives/a/aklomp-base64/0.5.2/test_package/test.c` — 编解码往返验证

## 验证结果

- 编译状态：通过（本地已验证 make lib/libbase64.o + ar 打包成功，L0/L1/L4/L5 全部通过）
- 上游测试执行情况：上游 test/ 目录 2 个测试程序（test_base64 编解码正确性 + benchmark 性能基准）已在 **build() 阶段编译验证**（conanfile.py 内 make -C test 构建）；OHOS CI 沙箱禁止执行 build 目录二进制（Operation not permitted），运行时验证在 OHOS 真机 PTY 完成
- 上游测试执行情况（NEON64）：test_base64 开启 NEON64（aarch64 原生 SIMD），实跑 NEON64 + plain 两个 codec 测试组（全部通过），每个 codec 组断言点约 828 个（8 测试向量×4 + 全字节表 256×2 + 流式 254 buffer + 无效输入 ~30），两组共约 1656 个断言点全部通过（输出 "all tests passed"）；benchmark 性能基准 6 组 buffer size 实跑通过
- 上游测试用例通过率：2/2 二进制（100%，test_base64 NEON64+plain 两组约 1656 断言点全过 + benchmark 通过）
- 新增测试用例通过率：1/1（100%，test_package encode/decode 往返一致，OHOS 真机 PTY 实测；CI 沙箱禁止 exec 非系统二进制（Operation not permitted），test_package 在 CI 中做编译链接验证）

## 补充说明

- **构建方式**：Makefile 一键构建，无 configure/autoreconf 需求
- **关键构建选项**：make lib/libbase64.o CC=clang NEON64_CFLAGS=-march=armv8-a（aarch64 开启 NEON64 原生 SIMD，其他 arch 不传）→ ar rcs libbase64.a；OHOS 无 cc，配方显式 CC=clang
- **补丁**：无（纯 libc 零依赖，无需 OHOS 适配补丁）
- **产物**：1 个静态库（libbase64.a）
- **依赖**：无外部 Conan 依赖（纯静态编译，libc-only）
- **上游测试说明**：test_base64.c 验证各 codec 编解码正确性（"all tests passed"）；benchmark.c 测量编解码吞吐量；两者均在 OHOS 真机编译运行通过（2/2），NEON64 + plain 两组 codec 覆盖约 1656 断言点
