# agent-browser 0.33.0 适配笔记

## 三重身份映射

- 平台身份：agent-browser / 0.33.0 / Issue #2138 / 分支 feat/agent-browser-0.33.0
- 上游身份：vercel-labs/agent-browser（GitHub），tag v0.33.0，Apache-2.0
- 归档身份：agent-browser/0.33.0（Conan），archives/a/agent-browser/0.33.0/
- 名称与版本在平台、上游、Conan 三侧完全一致，无需映射说明

## 编译环境

- 构建系统: cargo (Rust)，Cargo manifest 位于仓库 cli/ 子目录
- 编译日期: 2026-08-13
- 编译器: clang/clang++（Rust 工具链经 Harmonybrew bottle 引导安装，argc/1.24.0 先例）
- 状态: built（真机预检通过后由 HMBS 更新为 published）

## 编译步骤

agent-browser 是 Rust 编写的 AI 代理浏览器自动化 CLI（vercel-labs），
无 configure 步骤：

```bash
# 工具链：先探测设备上已有的 cargo（HNP 工具链 / harmonybrew / rustup），
# 探测不到时用 urllib 直接下载 Harmonybrew OHOS Rust bottle 并解包
# （不依赖 curl/zsh，设备 curl 无 CA bundle）
cargo build --release --manifest-path cli/Cargo.toml   # 构建 bin/agent-browser
cargo test --release --tests --manifest-path cli/Cargo.toml  # 上游测试（test_package 阶段）
```

配方要点：
- `source()`：`get()` 下载 GitHub tag 归档 v0.33.0.tar.gz（conandata.yml 为
  gh-proxy.com 镜像 + 官方 URL 的有序列表）并 strip_root
- `generate()`：写 `.cargo/config.toml`——clang 链接器 + rsproxy.cn sparse 镜像
  （设备无 crates.io CA bundle，直达 crates.io 会 TLS 失败）+ 网络容错
  （retry=10 / timeout=600 / low-speed-limit=1）
- `build()`：`_ensure_cargo()` 探测/引导 cargo → `cargo build --release
  --manifest-path cli/Cargo.toml`，仅构建产物；上游测试不在 build() 运行
  （hmbs 只采集 test_package 阶段标记，且包缓存命中时 build() 会被跳过）
- `package()`：候选路径探测 target/release 与 cli/target/release 下的
  agent-browser 产物并拷贝到 bin/
- `package_info()`：`cpp_info.bindirs = ["bin"]`
- test_package/conanfile.py `test()`：`/bin/sh test.sh`（3 消费者用例：
  --version / --help / doctor --offline --quick --json，输出
  HMBS_TEST_PACKAGE_RESULT）→ 镜像 cargo 引导 + 重新下载上游 tarball →
  `cargo test --release --tests --manifest-path cli/Cargo.toml`，解析
  "test result:" 行，`print()` 输出 HMBS_UPSTREAM_TEST_RESULT 标记

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 预检沙盒中 cargo/rustc 不在 PATH | hmbs 只注入 cmake/make/ninja/python3 | 先探测已知位置（HNP/harmonybrew/rustup/usr/local），无则引导 |
| 2 | curl 安装 Rust 工具链报 SSL 证书校验失败 | 设备 curl 无 CA bundle | 改用 Python urllib 直接下载 Harmonybrew OHOS bottle，先设置 SSL_CERT_FILE/CURL_CA_BUNDLE（argc/1.24.0 先例） |
| 3 | bottle 内 bin/cargo 等 wrapper 硬编码 Cellar 绝对路径 | 解包到 build 目录后路径不存在（rc=127） | 重写带 `.real` 同级的 `#!` wrapper 脚本为 exec 本地 `.real` 二进制 |
| 4 | cargo.real 动态链接 libssl/libcrypto/libz，OHOS loader 忽略 DT_RUNPATH | 无 RPATH 支持 | 把解包出的 openssl/zlib lib 目录放进 LD_LIBRARY_PATH |
| 5 | crates.io 直连 TLS 失败 | 设备无 crates.io CA bundle | .cargo/config.toml 用 rsproxy.cn sparse 镜像 + 网络容错 |
| 6 | doc-tests 阶段 rustdoc ENOENT | OHOS Rust 工具链（Harmonybrew bottle）无 rustdoc | `cargo test --release --tests` 排除 doc-tests 空阶段（martin/1.13.0、argc/1.24.0 平台限制先例） |
| 7 | 上游 e2e/parity 测试需要 Chrome | 上游已 `#[ignore]` 标记 | 按上游条件计为 ignored/skipped，不执行不伪造 |

## 上游测试

- 44 个测试模块（cli/src/*.rs），886 个 #[test] 单元测试
- cli/tests/doctor_cli.rs 集成测试（启动真实 CLI 验证 doctor 离线输出）
- e2e/parity 等需要 Chrome 的用例上游已 #[ignore]
- 最终统计以真机 cargo test "test result:" 框架输出行为准

## 消费者测试

- test_package/test.sh 3 个用例：`agent-browser --version` /
  `agent-browser --help` / `agent-browser doctor --offline --quick --json`
---

**编译结束**: 2026-08-14 01:41
**最终状态**: built
