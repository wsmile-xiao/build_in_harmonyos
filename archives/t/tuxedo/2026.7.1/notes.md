# tuxedo 2026.7.1 适配笔记

## 编译环境
- 构建系统: cargo（Rust，edition 2024）
- 编译日期: 2026-09-21
- 编译器: aarch64-unknown-linux-ohos-clang（链接器）+ rust-toolchain/1.97.1（rustc/cargo）
- 状态: built

## 软件信息
- 上游: https://github.com/webstonehq/tuxedo（键盘驱动的 todo.txt 终端 UI）
- 版本: 2026.7.1（上游 tag v2026.7.1 存在，来源 tarball sha256 259d46840f...2934）
- 产物: 可执行文件 `tuxedo`（默认引导 TUI；首个参数为 todo.sh 风格子命令时走 headless CLI）

## 编译步骤

配方 `conanfile.py` 走 tool_requires rust-toolchain/1.97.1（制品仓已发布，R36）：

1. `cargo build --release --locked --target aarch64-unknown-linux-ohos`
2. 上游测试 `cargo test --release --locked --target aarch64-unknown-linux-ohos --tests`（build() 内执行）
3. 产物 `target/aarch64-unknown-linux-ohos/release/tuxedo` 复制至包 bin/，并用
   binary-sign-tool 自签名（OHOS 拒绝未签名 ELF，EACCES）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cargo/rustc 无 code signature，OHOS loader 拒绝执行（EACCES） | rust-toolchain 包内为 rust-lang 官方 dist 预编译 tarball，ELF 未签名 | 复制 cargo/rustc + librustc_driver 到 build_folder 并用 binary-sign-tool -selfSign 1 自签名，其余只读负载软链（below/0.11.0 先例） |
| 2 | cargo 运行期加载 openssl/zlib 共享库失败 | OHOS loader 忽略 DT_RUNPATH | 下载 Harmonybrew OHOS bottle（openssl3/zlib/ca-certificates），显式 LD_LIBRARY_PATH（below/0.11.0 先例） |
| 3 | cargo 拉取 crate 依赖证书失败/网络受限 | 设备无默认 CA store | rsproxy.cn sparse 索引 + CARGO_HOME/config.toml 显式 cainfo，rustup 不可用（E105/E154：无法识别 HarmonyOS 宿主） |

## 依赖版本
- rust-toolchain/1.97.1（tool_requires，制品仓 ohpcd）
- 运行时 crate：anyhow 1.0.102 / chrono 0.4.44 / crossterm 0.29.0 / getrandom 0.2.17 / notify 8.2.0 / qrcode 0.14.1 / ratatui 0.30.0 / tiny_http 0.12.0
- dev：insta 1.47.2（快照测试）

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
conan test test_package tuxedo/2026.7.1
```
- 上游测试：见下节 R51 申报
- test_package：`bash test_tuxedo.sh`（7 项断言：--version/--help/add/list/listproj/done/done.txt 归档）

## 上游测试用例申报（R51 三步法）

### 1. 上游测试清点（静态统计）

| 测试类型 | 用例数 | 来源 |
|----------|--------|------|
| 集成测试（tests/snapshots.rs，insta 快照） | 21 | tests/snapshots.rs 中 `#[test]` 注册 |
| 单元测试（src/ 内嵌 `#[test]`） | ≥400 | src/**/*.rs 内 `#[test]` 宏（实测展开数见下） |

> 说明：上游用 cargo test 统一注册快照集成测试与单元测试，无独立 tests 脚本/
> ctest/pytest 注册。精确展开数由 build() 中 `cargo test` 实测统计回填。

### 2. 上游测试实际运行（OHOS aarch64）

- 运行方式：`cargo test --release --locked --target aarch64-unknown-linux-ohos --tests`
  （build() 内执行，HMBS_UPSTREAM_TEST_RESULT executed=469 passed=469 failed=0）
- 结果：**全部 469 项通过，0 失败**：
  - 单元测试 448 项全部通过（418 + 30，0 failed）
  - 快照集成测试 tests/snapshots.rs 21 项全部通过（0 failed）

### 3. 修复说明（原 18 项失败已修复）

| 补丁 | 修改 | 效果 |
|------|------|------|
| 0001-tests-snapshots.rs.patch | `FIXTURE_PATH`/`FIXTURE_CONFIG_PATH` 从硬编码 `/tmp/tuxedo-snapshot.txt` 改为相对路径 `tuxedo-snapshot.txt`（相对 cargo test 工作目录=源码根，可写） | 消除 OHOS `/tmp` erofs 只读导致的 `std::fs::write` 失败（Read-only file system errno 30） |
| 0002-0039-*.snap.patch（38 项） | 同步更新快照断言为相对路径渲染结果（`tuxedo-snapshot.txt`） | 快照与修改后的 fixture 路径一致 |

> 申报口径：上游完整注册 469 项（单元 448 + 快照 21）；OHOS 实测 **469/469 = 100% 通过**，
> 通过率 100%。原 18 项快照失败根因为上游硬编码 `/tmp`（OHOS erofs 只读），
> 已按 SKILL 尽力修复：将临时目录改为可写相对路径并同步更新快照断言。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/t/tuxedo/2026.7.1/conanfile.py | Conan 配方（application，tool_requires rust-toolchain） |
| archives/t/tuxedo/2026.7.1/conandata.yml | 官方源 + sha256 |
| archives/t/tuxedo/2026.7.1/test_package/ | 消费者测试（7 项断言） |
| archives/t/tuxedo/commands.json | CLI 工具声明（R38） |

## 注意事项
- 本项目无 C/C++ 编译依赖，依赖全部为纯 Rust crate，无需额外 requires 注入
- commands.json 按 R38 置于软件级目录（archives/t/tuxedo/）
---

**编译结束**: 2026-09-21 16:31
**最终状态**: built
