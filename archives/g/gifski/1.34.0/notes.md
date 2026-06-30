# gifski 1.34.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-05-25
- 编译器: clang 15.0.4
- Rust target: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

1. 下载 gifski 1.34.0 源码（GitHub tar.gz）
2. 添加 `.cargo/config.toml` 配置 OHOS 交叉编译：
   ```toml
   [target.aarch64-unknown-linux-ohos]
   linker = "clang"
   rustflags = ["-C", "link-arg=-fuse-ld=lld"]

   [env]
   CC = "clang"
   CXX = "clang++"
   ```
3. 移除 `Cargo.toml` 中的 `[patch.crates-io]` section（引用不可达的 ffmpeg-sys-next git repo）
4. 更新 `Cargo.lock` 依赖版本以适配当前可用 crates.io 包
5. cargo build：
   ```bash
   cargo build --release --no-default-features --features "binary,gifsicle"
   ```
6. cargo test：
   ```bash
   cargo test --release --no-default-features --features "binary,gifsicle"
   ```
7. 预编译包制作：ohc-run.py package gifski 1.34.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | [patch.crates-io] 引用不可达 git repo | ffmpeg-sys-next 的 fork repo 在 OHOS 编译环境不可达 | 移除 Cargo.toml 末尾的 [patch.crates-io] section |
| 2 | 无 OHOS 交叉编译配置 | Cargo 默认使用系统链接器 | 添加 .cargo/config.toml 配置 clang/lld 链接器 |
| 3 | Cargo.lock 依赖版本过期 | gifski 发布时的 lock 文件版本在当前 crates.io 不可用 | cargo update 更新依赖版本 |

## 源码修改

- `0001-Cargo.toml-remove-patch-crates-io-section.patch`: 移除 [patch.crates-io] section（不可达的 ffmpeg-sys-next git repo）
- `0002-dot-cargo-config.toml-add-ohos-cross-compile.patch`: 新增 .cargo/config.toml 配置 OHOS target 链接器
- `0003-Cargo.lock-update-dependency-versions.patch`: 更新依赖版本（aho-corasick、anstream、anstyle 等）

## 依赖版本

- imagequant: 4.3.4
- gif: 0.13.1
- gif-dispose: 5.0.1
- lodepng: 3.11.0
- clap: 4.5.32 (with cargo feature)
- resize: 0.8.8 (with rayon)
- rgb: 0.8.50

## 验证结果

```bash
# 单元测试: 16 passed, 0 failed
# 功能测试: gifski --version → gifski 1.34.0
# 质量门禁: PASS (G1/G2/G3/G4 all pass)
# Doc-tests: 跳过（rustdoc 在 OHOS musl 环境不可用，属平台限制而非 bug）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gifski-1.34.0-ohos-aarch64.tar.gz | 1.3MB | 预编译包（stripped） |
| gifski-1.34.0-ohos-aarch64-debug.tar.gz | 24KB | 调试符号包 |

## 注意事项

1. gifski 是 Rust crate，使用 cargo 构建系统而非 autotools/cmake
2. 编译时需设置 `--no-default-features --features binary,gifsicle`（默认启用 binary 和 gifsicle）
3. ffmpeg 视频输入功能（video feature）未启用，因 ffmpeg 在 OHOS 上需单独编译
4. rustdoc 在 OHOS musl libc 环境下不可用，doc-tests 跳过是预期行为
5. AGPL-3.0-or-later 许可证，商业使用需注意

---

**编译结束**: 2026-05-25 22:54
**最终状态**: built