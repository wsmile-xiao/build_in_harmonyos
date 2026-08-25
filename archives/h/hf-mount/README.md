# hf-mount

## 简介

hf-mount 将 Hugging Face Buckets 和 Hub 仓库通过 FUSE 或 NFS 挂载为本地文件系统。文件按需懒加载（首次读取才拉取网络字节），无需完整克隆或下载。

```bash
hf-mount start bucket myuser/my-bucket /tmp/data
hf-mount start repo openai/gpt-oss-20b /tmp/gpt-oss
```

两个后端：
- **NFS**（推荐）—— 无需 root、无内核扩展，全平台可用
- **FUSE** —— 内核集成更紧，需 root（Linux）或 macFUSE（macOS）

## 功能概述

- **懒加载**: 仅拉取代码实际读取的字节，节省磁盘与等待
- **Bucket 读写 + Repo 只读**: 支持两种 HF 存储形态
- **代理式存储**: Agent 直接用 `ls`/`cat`/`find`/`grep` 等 UNIX 管道操作远程数据
- **Advisory flock**: 单挂载内 Python `filelock` / `huggingface_hub` / `datasets` 缓存协调可用

## OHOS 适配

### 适配要点

- **构建系统**: Cargo（Rust），无需 configure 步骤
- **编译命令**: `cargo build --release --features nfs --bins`
- **后端选择**: 仅构建 NFS 后端（`--features nfs`）—— 无系统依赖、OHOS 可用；FUSE 后端需 libfuse3 + root，沙盒不可用
- **产物**: `bin/hf-mount`（管理 CLI）+ `bin/hf-mount-nfs`（NFS daemon）；`hf-mount-fuse` / `hf-mount-fuse-sidecar` 需 `fuse` feature，不打包
- **工具链**: OHOS 预检沙盒可能无 cargo/rustc，经 Harmonybrew 安装 Rust（argc/martin 先例）
- **链接器**: 设置 `CC=CXX=clang`、`RUSTFLAGS="-C linker=clang"`（OHOS 无 cc 符号链接）
- **TMPDIR**: OHOS /tmp 只读，构建与测试使用可写 TMPDIR
- **静态链接**: Rust 二进制默认静态链接，无 RPATH 需求
- **git 依赖**: xet-core、fuser fork 由 cargo 直接从 github.com 拉取，需网络可达
- **上游测试**: `cargo test --release --lib --bins`（src/ 379 个 #[test] 单元测试，用 MockHub/MockXet，全离线可执行）；tests/ 集成套件需 HF_TOKEN + 网络，离线不可运行

### 已知问题

- **FUSE 后端未构建**: OHOS PC 沙盒无 libfuse3 + root，FUSE 后端（`hf-mount-fuse` / `hf-mount-fuse-sidecar`）不打包；用户仅获得 NFS 后端 + 管理 CLI
- **集成测试不可运行**: tests/ 套件需 HF_TOKEN + 活网络到 huggingface.co（创建真实 bucket、挂载真实仓库），离线沙盒不可执行，如实记录为 unrunnable
