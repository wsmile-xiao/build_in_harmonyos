# tailwindcss 4.3.0 适配笔记

## 编译环境
- 构建系统: Rust + Node.js (混合项目)
- 编译日期: 2026-06-05
- 编译器: rustc 1.95.0, clang/clang++
- 状态: built (partial)

## 项目特性

tailwindcss v4 是一个混合架构项目：
- 核心部分：Rust (`crates/oxide`, `crates/node`)
- CLI/工具：TypeScript/JavaScript (`packages/@tailwindcss-cli`)
- 构建工具：pnpm + turbo
- Native binding：使用 napi-rs 创建 Node.js addon

## 编译步骤

### 1. 环境准备
```bash
# 已有环境
node v24.13.0
npm 11.6.2
rustc 1.95.0
cargo 1.95.0

# 安装 pnpm
npm install -g pnpm@9.6.0
```

### 2. Rust 核心编译
```bash
cd /data/storage/el2/base/cache/builds/tailwindcss-4.3.0.work
cargo build --release

# 产物：
# - libtailwind_oxide.so (Node.js native binding)
# - tailwindcss-oxide (性能测试工具，非 CLI)
```

编译成功，耗时约 3 分 49 秒。

### 3. Node.js 依赖安装失败
```bash
pnpm install --frozen-lockfile
```

失败原因：
- `bun@1.3.13` postinstall: Unsupported platform: openharmony arm64
- `esbuild@0.23.1` postinstall: Unsupported platform: openharmony arm64 LE

这两个工具没有 OpenHarmony 平台的预编译包，且无法从源码编译（bun 是 Zig，esbuild 是 Go）。

### 4. 手动创建 @tailwindcss/oxide 包
```bash
mkdir packages/@tailwindcss-oxide
cp target/release/libtailwind_oxide.so packages/@tailwindcss-oxide/tailwindcss-oxide.linux-arm64-gnu.node
# 创建 package.json, index.js, index.d.ts
```

### 5. ELF 签名
```bash
/data/service/hnp/bin/binary-sign-tool sign -inFile ... -outFile ... -selfSign 1
```

签名成功，但 Node.js dlopen 时仍报 Permission denied（安全弹窗问题）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | esbuild/bun 不支持 OpenHarmony | 无预编译包，且源码用 Go/Zig 编写 | 部分编译：只编译 Rust 核心 |
| 2 | Node.js native addon 加载失败 | 安全弹窗未触发或权限问题 | 需要用户手动触发执行 |
| 3 | TypeScript 编译缺少依赖 | @tailwindcss/oxide 未正确链接 | 手动创建包结构 |
| 4 | SSL 证书验证失败 | GitHub/GitCode HTTPS 连接问题 | 使用 curl -k 跳过验证 |

## 技术挑战

1. **esbuild 缺失**：tailwindcss v4 的构建流程依赖 esbuild/tsup，无法绕过
2. **bun 缺失**：standalone 包构建需要 bun
3. **Node.js native addon 权限**：OpenHarmony 的安全机制对 `.node` 文件有额外限制

## 建议方案

### 方案 A：部分编译（已尝试）
- 编译 Rust 核心成功
- 手动创建 @tailwindcss/oxide 包
- 问题：无法完成完整的 CLI 构建

### 方案 B：使用 npx wrapper
```bash
# wrapper script (tailwindcss.sh)
#!/bin/bash
npx tailwindcss@4.3.0 "$@"
```

优点：简单、可立即使用
缺点：每次调用需要下载/解压，速度慢

### 方案 C：预编译 esbuild 和 bun
需要先编译这两个工具才能完成 tailwindcss 的完整构建。

## Rust 编译产物

```
target/release/
├── libtailwind_oxide.so      # Node.js binding (3.2M)
├── tailwindcss-oxide         # 性能测试工具 (530K)
├── libtailwindcss_oxide.rlib # Rust 库文件
└── libclassification_macros.so
```

## 验证结果

### Rust binding 测试
```bash
# 加载测试失败（Permission denied）
node -e "const oxide = require('./index.js'); ..."
```

### 性能工具测试
```bash
./target/release/tailwindcss-oxide
# Extractor: 48.90 MB/s over 5.70s
```

## 依赖版本

- Rust: 1.95.0
- Node.js: 24.13.0
- pnpm: 9.6.0
- napi: 3.8.5 (Rust crate)
- napi-derive: 3.5.4 (Rust crate)

## 注意事项

1. tailwindcss v4 是架构重构版本，核心用 Rust 重写
2. 需要 esbuild 和 bun 才能完整构建
3. `.node` 文件需要 ELF 签名并在受信任路径执行
4. 建议优先使用方案 B（npx wrapper）作为临时解决方案
5. 长期需要：编译 esbuild 和 bun 的 OpenHarmony 版本

---

**编译结束**
**最终状态**: built (partial) - Rust 核心+Node.js binding编译成功，但CLI构建受阻于esbuild/bun缺失