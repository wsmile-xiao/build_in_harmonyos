# libimagequant 4.4.1 适配笔记

## 编译环境
- 构建系统: cargo（Rust workspace，上游 4.x 已迁移纯 Rust 实现 + C FFI）
- 编译日期: 2026-09-10
- 编译器: rust-toolchain/1.97.1（conan tool_requires）+ clang（交叉链接器）
- 状态: built

## 背景与选型核实

libimagequant 是 pngquant 的量化核心库。上游 4.x 系列**已将实现从纯 C
迁移为纯 Rust**（Cargo workspace：`imagequant` Rust lib crate +
`imagequant-sys` C FFI staticlib crate），tarball 内**没有 CMakeLists.txt**
（平台任务情报中"CMake + LIQ_NATIVE 选项"对应的是 2.x 纯 C 时代的构建
形态）。C 消费接口 `imagequant-sys/libimagequant.h` 保持稳定
（LIQ_VERSION 40003 / "4.0.3"），pngquant/GIMP 等下游的链接消费形态不变
——conan 打包形态仍是**纯 C API 静态库**（libimagequant.a + libimagequant.h）。

三维核验：
- 制品仓：`conan install --requires=libimagequant/*` → not found（无冲突）
- 平台归档：archives/l/libimagequant/2.18.0 仅为 manifest 骨架（无
  conanfile.py/test_package，未制品化发布），4.4.1 为全新适配
- 上游：GitHub tag 4.4.1 实存（最新正式版）

## 编译步骤

1. `tool_requires: rust-toolchain/1.97.1 + openssl/3.5.6.1.1`
2. Rust 运行时准备（OHOS HMDFS 执行标签限制 E046 同类）：
   - `binary-sign-tool sign -selfSign 1` 签名 cargo/rustc/
     librustc_driver*.so 私有拷贝（cbindgen 0.28.0 先例）
   - openssl 静态归档 `-Wl,--whole-archive` relink 出私有
     libssl.so/libcrypto.so 供 cargo 运行时（系统 libssl 缺
     SSL_get0_group_name 等 3.0 符号）
   - rustc sysroot 通过 `<runtime>/bin/rustc` + `lib -> 真实 rustlib`
     符号链接树自行推导
3. `.cargo/config.toml`：rsproxy.cn sparse 镜像 + certifi CA +
   `[target.aarch64-unknown-linux-ohos] linker = clang`
4. `cargo build --release -p imagequant-sys --target aarch64-unknown-linux-ohos`
   → `target/aarch64-unknown-linux-ohos/release/libimagequant_sys.a`
5. package：规范化库名 libimagequant_sys.a → libimagequant.a +
   libimagequant.h + COPYRIGHT

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rust-toolchain 二进制 Permission denied | HMDFS 执行标签限制（E046 同类），chmod 无效 | binary-sign-tool 对私有拷贝自签（cbindgen 先例） |
| 2 | cargo 报 libssl.so 缺 SSL_get0_group_name | 系统 libssl 版本过旧（无 3.0 符号） | openssl conan 包静态归档 relink 私有 .so |
| 3 | cargo 下载 crates 报 self-signed certificate | worker 无根证书 | certifi.where() 注入 cainfo |
| 4 | 上游 tarball 无 Cargo.lock，`--locked` 失败 | tag 归档不含 lock 文件 | build/test 均不加 --locked |
| 5 | c_test 的 build.rs 找不到 cc | OHOS worker 只有 clang 无 cc/gcc 符号链接 | symlink clang → cc/gcc（scooter 先例） |
| 6 | crates.io 直连超时 | 网络环境 | rsproxy.cn sparse 镜像替换源 |

## 验证结果

```bash
# 1. 交叉构建静态库
cargo build --release -p imagequant-sys --target aarch64-unknown-linux-ohos
# → libimagequant_sys.a 23.6MB (ar archive) PASS

# 2. 上游测试（cargo test --release --workspace --tests）
#    c_test: 1 passed; imagequant: 16 passed; imagequant-sys ffi: 4 passed
#    → 21/21 PASS（0 失败）

# 3. C 消费者 roundtrip（pngquant 同款用法）
clang -O2 -I imagequant-sys liq-consumer.c libimagequant_sys.a -lpthread -lm -ldl
./liq-consumer
# → palette entries: 4 / remap roundtrip OK / consumer test PASS
```

## 依赖版本

- rust-toolchain/1.97.1（制品仓，!8610）
- openssl/3.5.6.1.1（制品仓，cargo 运行时 libssl/libcrypto relink 源）
- crates.io: arrayvec 0.7.8, rgb 0.8.53, once_cell 1.21.4,
  rayon 1.x, thread_local 1.1.10, bitflags 2.13.2, libc 0.2.189

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libimagequant.a | Rust core 静态库（规范化名） |
| include/libimagequant.h | C API 头文件 |
| licenses/COPYRIGHT | 上游版权声明 |

## 注意事项

- 4.x 上游为 Rust 实现：下游 C 消费者链接时需 -lpthread -lm -ldl
  （Rust std 线程运行时），recipe 的 cpp_info.system_libs 已声明。
- librustc_driver.so 签名拷贝随 LD_LIBRARY_PATH 传递；构建机无
  binary-sign-tool 时（Linux worker）直接用 rust-toolchain 包内原生
  二进制，逻辑已双路径兼容。
- 上游 threads 特性默认启用（rayon 并行），静态库线程安全。
