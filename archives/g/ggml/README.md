# ggml

## 简介

ggml是一个用于机器学习的张量库，专注于在普通硬件上实现大型模型的高效推理。它是llama.cpp、whisper.cpp等项目的核心依赖库。

## 主要特性

- **高效推理**：优化的CPU/GPU实现，支持量化推理
- **跨平台**：支持多种操作系统和硬件架构
- **灵活后端**：支持CPU、CUDA、Metal、Vulkan等多种后端
- **轻量级**：无外部依赖，易于集成

## 编译信息

- **版本**：latest (master分支)
- **构建系统**：CMake
- **编译器**：clang/clang++ 15.0.4
- **平台**：OpenHarmony (aarch64)

## 依赖

无外部依赖。内置OpenMP和pthread支持。

## 安装

### 从预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ggml latest
```

### 从源码编译

```bash
git clone https://github.com/ggerganov/ggml.git
cd ggml
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
make install
```

## 使用示例

```c
#include <ggml.h>

int main() {
    // 创建ggml上下文
    struct ggml_init_params params = {
        .mem_size   = 16*1024*1024,
        .mem_buffer = NULL,
        .no_alloc   = false,
    };

    struct ggml_context * ctx = ggml_init(params);

    // 创建张量
    struct ggml_tensor * a = ggml_new_tensor_1d(ctx, GGML_TYPE_F32, 128);

    // 使用ggml进行计算...

    ggml_free(ctx);
    return 0;
}
```

## 链接

- 主页：https://github.com/ggerganov/ggml
- 文档：https://github.com/ggerganov/ggml/tree/master/docs

## 许可证

MIT License

## 注意事项

1. OpenHarmony平台适配：CMake检测为UNKNOWN平台，回退到generic实现
2. 编译警告：部分clang编译参数（-mfma, -mf16c, -mavx, -mavx2）在ARM架构上未使用
3. OpenMP支持：已启用（版本5.0）

## 版本历史

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| latest | built | 2026-06-05 | 首次编译成功 |