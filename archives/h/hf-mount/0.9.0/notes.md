# 适配笔记 — hf-mount 0.9.0

## 上游身份

- 项目：huggingface/hf-mount
- 仓库：https://github.com/huggingface/hf-mount
- tag/version：v0.9.0
- 源码 URL：https://github.com/huggingface/hf-mount/archive/refs/tags/v0.9.0.tar.gz
- SHA256：5b605ae805c05a1238eca341795a0718581c757e31677d8a088bc00707c31acc
- 许可证：Apache-2.0
- 语言/构建：Rust / Cargo（edition 2024，workspace）
- Rust 要求：1.89+（Harmonybrew bottle 提供 1.97.1）

## 归档身份

- Conan name/version：hf-mount/0.9.0
- archives 路径：archives/h/hf-mount/0.9.0/
- commands.json：软件级（tool 类型，binary=true）

## 适配方案（路径 A 最小完整）

- 后端选择：仅构建 NFS（`--features nfs`）——无系统依赖、OHOS 可用；FUSE 需 libfuse3 + root，沙盒不可用
- 产物：`bin/hf-mount`（管理 CLI）+ `bin/hf-mount-nfs`（NFS daemon）；`hf-mount-fuse` / `hf-mount-fuse-sidecar` 需 `fuse` feature，不打包
- 工具链：probe cargo → 无则 Harmonybrew bottle bootstrap（argc/martin 先例）；CC/CXX=clang，RUSTFLAGS='-C linker=clang'
- 网络：crates.io 经 rsproxy.cn sparse 镜像（设备无 CA bundle，直达 TLS 失败）；git 依赖（xet-core, fuser fork）由 cargo 直拉 github.com
- TMPDIR：~/tmp/hf-mount（OHOS /tmp 只读）
- 串行构建：CARGO_BUILD_JOBS=1, MAKEFLAGS=-j1（git deps + -sys crates 链接可靠，martin 先例）

## 测试契约

### 上游测试

- 入口：`cargo test --release --lib --bins --skip overlay`（src/ 单元测试，用 MockHub/MockXet，离线可执行）
- 实际运行（真机 conan create test_package 阶）：lib+bin 总 344 个 #[test]，310 passed，0 failed，34 platform_unrunnable
- 真实分布（344 总）：error.rs(2) / hub_api.rs(44，含子模块) / file_cache.rs(10) / cached_xet_client.rs(6) / virtual_fs/inode.rs(48) / virtual_fs/prefetch.rs(29) / virtual_fs/flush.rs(12) / virtual_fs/poll.rs(15) / virtual_fs/staging.rs(5) / virtual_fs/tests.rs(197 中可运行 60) / overlay.rs(4) / bin/hf-mount.rs(0) / bin/hf-mount-fuse-sidecar.rs(3，fuse feature gated 不计)
- 平台不可运行（SIGSYS signal 31，OHOS PC 未实现 syscall，如实记录为 unrunnable，不改为 skipped）：34 个 = overlay 模块 4 + virtual_fs::tests syscall 族 30（symlink/rename/readdir/rmdir/unlink/mkdir/mknod/create/mount/stat/truncate/chmod/chown/utimens/setattr/fcntl/flock/lock 等未实现 syscall，触 SIGSYS 杀整个测试二进制，cargo 无法逐用例汇总；真机 probe 实测 --skip overlay 后余 310 全通过）
- 不可运行（环境限制，如实记录为 unrunnable，不改为 skipped）：tests/ 集成套件 12 个入口，全部需 HF_TOKEN + 活网络到 huggingface.co（setup_bucket 创建真实 bucket、mount_repo 挂载真实仓库 openai-community/gpt2）
- doc-tests：OHOS rust 工具链无 rustdoc（ENOENT），hf-mount 源 0 doctest，排除空阶段（martin/argc 先例）

### 消费者测试

- test_package/test.sh：3 个用例——hf-mount --version / --help / status（无运行 daemon），真机 conan create test_package 阶 3/3 通过
- assertion_count：3

## 补丁

无。上游 0.9.0 直接构建，未改源码。

## 已知限制

- FUSE 后端未构建（沙盒无 libfuse3 + root）
- tests/ 集成套件不可运行（需 HF_TOKEN + 网络）
---

**编译结束**: 2026-08-18 22:20
**最终状态**: built
