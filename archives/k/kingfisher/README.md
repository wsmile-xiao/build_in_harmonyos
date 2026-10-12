# kingfisher

MongoDB's blazingly fast and accurate secret scanning and validation tool.
It detects leaked credentials in files, Git history, archives and cloud
storage, and can validate many of the findings against the live provider API.

- **Homepage**: https://github.com/mongodb/kingfisher
- **License**: Apache-2.0
- **Category**: security
- **Build system**: cargo (Rust 2024 edition, `rust-version = 1.96`)

## 开源信息

| 项 | 值 |
|---|---|
| 软件名 | kingfisher |
| 上游版本 | **v1.109.0**（包版本 `kingfisher/1.109.0`，与上游一致） |
| 上游仓库 | `https://github.com/mongodb/kingfisher` |
| 官方源码 | `https://github.com/mongodb/kingfisher/archive/refs/tags/v1.109.0.tar.gz` |
| 源码 sha256 | `d1c6c9bdcae956709a30cf208dd368fb047c53bd6114019782e000b94d57682d` |
| 开源许可 | **Apache-2.0**（上游 `LICENSE`；制品内随包分发于 `licenses/LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES`） |
| 适配路径 | 路径 A（基础适配） |
| 使用知识库 | E210（mimalloc `MI_MALLOC_OVERRIDE` 覆盖系统 `malloc`/`free` 与鸿蒙内存管理冲突 → 启动期 SIGSEGV）；项目内置 SKILL 流程（R47 语言预检 / R51 上游测试三步法 / R32 平台判断 / R38 commands.json） |
| 补丁 | `1.109.0/patches/0001-mimalloc-disable-override.patch` —— 唯一源码改动 1 行，关闭 mimalloc 的 `override` feature（退出码 `139 → 0`），无平台宏注入（不违反 R8） |
| 测试摘要 | 上游清点 911 个 `#[test]`（`tests/` 240 + 单元 671）；实测 **784 passed / 0 failed / 2 ignored**，另有 3 个外部环境依赖用例按测试质量规范 §3.3 豁免并逐条声明（未删改上游测试源码）；消费者视角 `test_package` **PASS 4/4** |
| 制品 | `bin/kingfisher`（OHOS aarch64，经 `binary-sign-tool` 自签名）+ `licenses/` |
| 构建系统 | cargo（`cargo build --release --locked`，`Cargo.lock` 锁定，Conan 制品依赖 0） |

## Features

- Regex rule engine over a large built-in ruleset (vectorscan/ hyperscan
  compiled patterns), with language-aware and entropy heuristics.
- Scans files, directories, Git history, archives and remote sources.
- Validators that confirm whether a detected credential is still live.
- Multiple output formats (`json`, `json-line`, `sarif`, and plain text).

## OHOS adaptation

- Builds the upstream tag `v1.109.0` with `cargo build --release --locked`;
  `Cargo.lock` pins the whole crate graph, so there are zero Conan artifact
  dependencies.
- `rustc` reports `target_os = "linux"` / `target_env = "ohos"` on this target,
  so upstream's `any(feature = "use-mimalloc", target_os = "linux", ...)` guard
  is always true and mimalloc cannot be disabled with
  `--no-default-features`.
- The single source patch disables mimalloc's `override` feature: on HarmonyOS
  `MI_MALLOC_OVERRIDE` replaces the system `malloc`/`free`, which conflicts with
  the platform memory manager and makes the binary crash (SIGSEGV, exit 139)
  before `main()`. mimalloc is still linked as a regular allocator.
- The vendored `vectorscan-rs` engine is built by CMake and needs `clang++`
  (exposed as `cc`/`c++` shims) plus Boost >= 1.61 headers.
- `aws-lc-sys` needs a CMake toolchain overlay pinning
  `CMAKE_SYSTEM_PROCESSOR=aarch64`, otherwise it derives `ARCH=generic` and
  silently drops every s2n-bignum assembly file, which fails at link time.
- The packaged ELF must be signed with `binary-sign-tool`; OHOS refuses to
  execute unsigned binaries.

## Usage

```bash
conan install --requires=kingfisher/1.109.0

kingfisher --version
kingfisher scan /path/to/source
kingfisher scan -f json /path/to/source
```

## Related

- Upstream test suite: Rust built-in `libtest` (`cargo test --release`),
  44 integration test files plus workspace unit tests.
- Adaptation notes and the exact build environment: `1.109.0/notes.md`.
- Upstream test counts, exemptions and consumer assertions:
  `1.109.0/test_package/MANIFEST.yml`.
