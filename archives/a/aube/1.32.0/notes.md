# aube 1.32.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust workspace)
- 编译日期: 2026-08-25
- 编译器: rustc 1.97.1, cargo 1.97.1, clang 15
- Rust 目标: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

1. 下载源码：aube-1.32.0.tar.gz (GitHub v1.32.0)
2. 解压到构建目录
3. 设置 `.cargo/config.toml` 指定 `aarch64-unknown-linux-ohos` 的 linker 为 clang
4. 设置 `AUBE_PRIMER_PATH` 为空 primer，避免 build.rs 在编译期访问 npm registry
5. 设置 `OHOS_SDK_NATIVE` 与修正后的 CMake toolchain（将 `llvm-ranlib` 指向 `llvm-ar`），使 aws-lc-sys 能完成 OHOS 汇编构建
6. 执行 `cargo build --release --target aarch64-unknown-linux-ohos -p aube --bin aube`
7. 复制 `aube` 到 `bin/`
8. 执行 `aube --version` 与 `aube --help` 验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc 默认 linker `cc` 不存在 | OHOS 环境没有 `cc` | 在 `.cargo/config.toml` 中为 OHOS target 指定 `linker = "clang"` |
| 2 | aube-resolver build.rs 尝试调用 node 生成 primer | 源码未携带 primer 数据文件 | 设置 `AUBE_PRIMER_PATH` 指向空文件，构建期跳过生成 |
| 3 | /tmp 只读 | OHOS 文件系统限制 | 设置 `TMPDIR=~/tmp/aube` |
| 4 | aws-lc-sys 链接缺少 AArch64 汇编符号 | 未使用 OHOS CMake toolchain 构建 | 设置 `OHOS_SDK_NATIVE` 并使用修正 ranlib 路径的 toolchain wrapper |
| 5 | aws-lc-sys 的 `llvm-ranlib` 不存在 | 当前 OHOS SDK llvm/bin 未提供该工具 | toolchain wrapper 将 `CMAKE_RANLIB` 指向 `/data/service/hnp/bin/llvm-ranlib` |

## 源码修改

无 aube 源码修改；仅构建期通过环境变量/CMake toolchain wrapper 适配。

## 验证结果

```bash
$ aube --version
1.32.0 linux-arm64 (2026-08-25)

  aube 2.1.0 is available (current: 1.32.0)
  upgrade: https://aube.jdx.dev

$ aube --help
A fast Node.js package manager

Usage: aube [OPTIONS] [COMMAND]
...
```

上游测试完整执行（本地 CI 模拟）：
- `cargo test --workspace`（含全部 14 个 crate）：2220 passed / 6 failed
  - 6 个失败均为 OHOS 环境差异（非代码缺陷）：
    - `aube` engines 权限测试：OHOS 文件系统不强制 chmod 000 权限拒绝
    - `aube-linker` symlink 模式 / reflink 回退：OHOS 文件系统权限位与 reflink 能力差异
    - `aube-resolver` glibc/musl 主机判定：OHOS 非 glibc Linux 主机
    - `aube-store` 文件权限位：OHOS umask 默认值不同
- BATS 集成测试：110/111 个文件已执行（`vlt_benchmarks.bats` 依赖外部 npmjs 网络未跑），
  失败项均为 OHOS 环境差异（jailBuilds 沙箱、exec 信号、runtime_download 镜像、缺 jq 等）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aube | 30 MB | 主二进制 |

## 注意事项

1. 编译时间较长，依赖数量多
2. 使用空 primer 构建的版本在无网络时无法解析未缓存的包元数据，属预期行为
3. 首次运行可能需要用户确认安全弹窗
