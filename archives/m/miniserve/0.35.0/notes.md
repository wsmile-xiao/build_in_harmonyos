# miniserve 0.35.0 适配笔记

## 软件信息

- **软件名**: miniserve
- **版本**: 0.35.0
- **上游仓库**: https://github.com/svenstaro/miniserve
- **标签**: v0.35.0
- **描述**: For when you really just want to serve some files over HTTP right now!
  轻量静态文件 HTTP 服务器，支持目录浏览、归档下载（tar/zip）、上传、WebDAV、TLS、认证等。
- **许可证**: MIT
- **构建系统**: Cargo (Rust, edition 2024)
- **语言**: Rust
- **源码位置**: /storage/Users/currentUser/builds/miniserve-0.35.0.work/

## 编译环境

- 构建系统: cargo
- 编译日期: 2026-08-09
- 编译器: rustc 1.97.1（host = aarch64-unknown-linux-ohos）+ OHOS clang 15.0.4（linker/cc-rs）
- 目标: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

```bash
# 环境（cc-rs 需要 CC/AR，rustc 需要 OHOS linker）
export PATH=/data/service/hnp/bin:$PATH
export CC=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang
export AR=/storage/Users/currentUser/.harmonybrew/bin/llvm-ar

# rustc host 本身就是 aarch64-unknown-linux-ohos，无需显式 --target
cargo build --release
```

注意：`CC_aarch64-unknown-linux-ohos` 等带连字符的变量名不能作为 POSIX sh 前缀赋值，
配方中必须用 `env CC_aarch64-unknown-linux-ohos=... cargo build ...` 形式传递。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error occurred in cc-rs: failed to find tool "cc"` | zstd-sys（actix-web compress-zstd 特性）等 C 依赖经 cc-rs 编译，OHOS 无 `cc` | CC/AR 环境变量指向 aarch64-unknown-linux-ohos-clang / llvm-ar |
| 2 | 链接阶段 rustc 默认 linker `cc` 不存在 | OHOS 环境无通用 cc | 配方内设 `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER` 指向 OHOS clang（不依赖 ~/.cargo/config.toml） |
| 3 | test_package 运行报 Operation not permitted | OHOS ELF 未签名 | package() 内 llvm-objcopy 去 .codesign + binary-sign-tool -selfSign 1 重签 |
| 4 | conan create 后 package() 找不到二进制 | cargo 从 build 目录向上找到源码 Cargo.toml，target 产物落在 source_folder | package() 同时检查 source_folder 与 build_folder 两处 target/release/miniserve |
| 5 | 上游测试二进制运行 exit=126 Permission denied | 签名后产物权限位丢失（-rw-rw----） | chmod +x 恢复执行位（配方 _sign_elf 中 os.chmod(path, 0o755)） |
| 6 | tls/auth_file 套件首跑全失败 | 从 target/release/deps 目录手动跑测试，相对路径 tests/data/ 找不到 | 从源码根目录重跑（cargo test 的正常 cwd），5 套件中 tls、auth_file 复跑全过 |

## 源码修改

无（补丁为零）。源码原样 cargo 构建成功。

## 依赖版本

- rustc/cargo 1.97.1（homebrew 提供的 OHOS 适配版，含 aarch64-unknown-linux-ohos std）
- OHOS clang/llvm-ar/binary-sign-tool：/data/service/hnp/bin/
- crate 依赖全部来自 crates.io，Cargo.lock 锁定（actix-web 4.13.0、actix-files 0.6.10、
  dav-server 0.11.0、rustls、zstd 等，无 C/C++ 系统库依赖）

## 验证结果

- conan-verify 门禁：G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS
- 上游测试：cargo test 全量 282 用例，278 通过 / 4 失败（全部为 OHOS 平台限制，见 test-report.md），
  通过率 278/282 = 98.58%
- test_package 消费者测试：--version + 真实 HTTP 服务 + curl 抓取，3 项全过

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 4.5K | Conan 2 配方（cargo 构建 + ELF 签名） |
| conandata.yml | - | crates.io 官方源 + SHA256 |
| test_package/ | - | 消费者视角冒烟测试（version + HTTP serve + curl） |
| packaging/miniserve-0.35.0-ohos-aarch64.tar.gz | - | 产物包（已签名 miniserve 二进制） |
| reports/conan-verify-report.md | - | 门禁报告 |
| reports/test-report.md | - | 上游测试全量报告 |

## 注意事项

1. crates.io .crate 是 gzip tar（cargo 注册表标准分发格式），conan get() 需显式命名 filename 为
   `.tar.gz` 才能走 tar 解压分支（同 tlrc 先例）。
2. 本机 rustc host 恰为 aarch64-unknown-linux-ohos，故配方不传 --target；若 CI 环境 rustc host
   是其他 triple，需在配方 build() 中按 settings.arch 显式加 `--target aarch64-unknown-linux-ohos`。
3. 上游测试中 4 个失败用例均为 OHOS 平台限制（hmfs 符号链接环检测、IPv4/IPv6 双栈绑定、
   权限位不完整保留），非库缺陷，详见 reports/test-report.md。
4. 与 tlrc 配方的差异：tlrc 的 package() 只查 build_folder 一个位置（其 conan-verify 曾因此
   G2 FAIL——binary not found），miniserve 配方双路径查找规避该坑。

## 结束标记

最终状态: published
