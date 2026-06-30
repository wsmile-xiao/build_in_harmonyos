# kubie 0.26.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- Rust: cargo 1.95.0
- 状态: built

## 编译步骤

```bash
# 1. init-build
python3 $SKILL_ROOT/scripts/ohc-run.py init-build kubie 0.26.0 --url=https://gh.idayer.com/sbstp/kubie/archive/refs/tags/v0.26.0.tar.gz

# 2. 应用补丁（替换aws-lc-rs为ring作为TLS crypto backend）
patch -p1 < archives/k/kubie/0.26.0/patches/0001-Cargo.lock.patch
patch -p1 < archives/k/kubie/0.26.0/patches/0002-Cargo.toml.patch

# 3. Cargo编译
cd $BUILD_SRC_DIR
cargo build --release --target aarch64-unknown-linux-ohos

# 4. 复制二进制
cp target/aarch64-unknown-linux-ohos/release/kubie $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp target/aarch64-unknown-linux-ohos/release/kubie $TEST_PREFIX/bin/
cp target/aarch64-unknown-linux-ohos/release/kubie $DEFAULT_PREFIX/bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws-lc-rs linking失败（undefined reference to aws_lc_0_29_0_bignum_*） | OHOS平台上aws-lc-sys native C库编译链接失败 | 添加rustls依赖使用ring作为crypto backend替代aws-lc-rs |

## 源码修改

- Cargo.toml: 添加 `[dependencies.rustls]` with `features = ["ring", "std", "tls12"]`
- Cargo.lock: 添加 ring 作为 rustls 的依赖

## 依赖版本

- Rust/cargo: 1.95.0
- clang: 15.0.4

## 验证结果

```bash
$DEFAULT_PREFIX/bin/kubie --version
kubie 0.26.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| kubie-0.26.0-ohos-aarch64.tar.gz | 3917KB | 预编译包（含bin/kubie） |

## 注意事项

- 必须使用 `--target aarch64-unknown-linux-ohos` 编译
- 默认feature `update` 引入 attohttpc + rustls + aws-lc-rs，OHOS上需替换为ring backend
- 二进制已strip，为ELF PIE executable (dynamic)
---

**编译结束**: 2026-06-08 20:33
**最终状态**: built
