# yazi 26.5.6 编译笔记

## 项目信息
- **软件**: yazi (文件管理器)
- **版本**: 26.5.6
- **构建系统**: Rust (cargo)
- **目标平台**: HarmonyOS NEXT (musl libc, aarch64)

## 编译环境
- **Rust**: rustc 1.96.0, cargo 1.96.0
- **CC**: ohos-clang wrapper (替换 --target=aarch64-unknown-linux-musl → --target=aarch64-linux-ohos)
- **CXX**: ohos-clang++ wrapper
- **AR**: llvm-ar
- **RANLIB**: llvm-ranlib
- **TMPDIR**: /data/storage/el2/base/haps/entry/temp

- **RUSTFLAGS**: -C linker=ohos-clang

## 源码修改
### 1. 移除 tikv-jemallocator
- yazi-fm/Cargo.toml 移除了 tikv-jemallocator 依赖（在 HMDFS 上 configure 无法创建临时文件）
- yazi-fm/src/main.rs 移除了 #[global_allocator] 属性和 static GLOBAL 声明
- 使用系统默认内存分配器代替 jemalloc

### 2. Cargo.lock 更除 tikv-jemallocator 引用
- Cargo.lock 自动移除了 tikv-jemallocator 相关条目

### 3. C 编译器适配
- 创建了 ohos-clang 和 ohos-clang++ wrapper 脚本
- 将 --target=aarch64-unknown-linux-musl 替换为 --target=aarch64-linux-ohos
- 添加 OHOS sysroot 和 include 软径
- 这是平台适配，不是软件问题

## 编译命令
```bash
export TMPDIR=/data/storage/el2/base/haps/entry/temp
export PATH=/storage/Users/currentUser/tmp/bin:$PATH
export CC="ohos-clang" CXX="ohos-clang++"
export CC_aarch64_unknown_linux_musl="ohos-clang"
export CXX_aarch64_unknown_linux_musl="ohos-clang++"
export AR="llvm-ar" RANLIB="llvm-ranlib"
export RUSTFLAGS="-C linker=ohos-clang"

cargo build --release
```

## 安装
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp target/release/yazi $TEST_PREFIX/$DEFAULT_PREFIX/bin/yazi
cp target/release/ya $TEST_PREFIX/$DEFAULT_PREFIX/bin/ya
```

## 签名验证
- 所有 ELF 二进制必须使用 ohc-run.py sign-elf 签名
- yazi 26.5.6 正常运行
- ya 26.5.6 正常运行

