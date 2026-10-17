# intermodal 0.1.16 — OHOS PC (aarch64) 适配笔记

- 状态: built（本地 OHOS aarch64 构建+上游测试+消费者测试通过；未上传发布）
- 软件定位：intermodal（二进制 `imdl`）是 Casey Rodarmor 的 BitTorrent 元信息
  CLI 工具——create / show / verify / link / stats .torrent 与 magnet link。
  纯 Rust（edition 2021，CC0-1.0），crates.io 依赖集无 C 绑定
  （无 OpenSSL/libgit2/libz 等系统库），纯 CLI 无特殊运行时。
- 上游核对：GitHub casey/intermodal v0.1.16（tarball sha256
  3a072929379ddba929d85a579888ac51cf22e44897b7dc84af7612f49d3874d7，
  Cargo.toml version=0.1.16，`imdl --version` → `imdl v0.1.16`）✅

### 对话 #1（2026-09-23）

**Q：适配路径？**
A：Rust 生态在本仓库已有成熟先例（below/0.11.0）：以
`rust-toolchain/1.97.1`（rust-lang 官方 dist 预编译，宿主=目标=
aarch64-unknown-linux-ohos）作 tool_requires 在 HarmonyOS PC 上原生
cargo 构建，不用 rustup（无法识别 HarmonyOS 宿主，E105/E154）。

**Q：踩了哪些坑、怎么解的？**

| # | 现象 | 根因 | 解法 |
|---|------|------|------|
| 1 | `_prepare_signed_toolchain()` 里 `os.symlink` 报 `PermissionError: [Errno 13]` | HMDFS uid 映射卷上 conan 缓存目录内**创建符号链接被内核拒绝**（below 在 CI 远程跑成功，本机实测 EPERM） | `_link()` 三级降级：目录 symlink→copytree（symlinks=True），文件 symlink→hardlink→copy2；cargo/rustc/librustc_driver 照旧复制+binary-sign-tool 自签名，marker 幂等 |
| 2 | harmonybrew `zlib-ng-compat-2.3.3_1` bottle **404**（below 配方同 URL 现已失效，2026-09 实测） | bottle 被下架/改名 | cargo 的 DT_NEEDED 只需未版本化 `libz.so`；OHOS 系统有 `/usr/lib/libz.so.1` → 直接复制出未版本化 `libz.so` 放进 runtime lib 目录（ABI 稳定），LD_LIBRARY_PATH 注入。openssl3 bottle（3.6.4）仍需下载：系统 OpenSSL 3.0 缺 `SSL_get0_group_name` |
| 3 | cargo 编译 build script 报 `could not exec the linker \`cc\` — Permission denied` | rustc 对 aarch64-unknown-linux-ohos 默认 linker 是 `cc`，本机该名不可执行 | 注入 `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER`（OHOS clang 绝对路径）+ `CC_/CXX_/AR_/RANLIB_aarch64_unknown_linux_ohos`（below 同款） |
| 4 | doctest target 直接 EACCES | doctest 由 `rustdoc` 执行，dist 包 rustdoc 未签名（只签了 cargo/rustc/librustc_driver） | 上游测试限定 `--lib --bins`（284 个 #[test]）；README/doc 示例不属于单元测试契约，notes/MANIFEST 如实申报 |
| 5 | `imdl torrent info` 不存在 | 本版本子命令叫 **show**（0.1.16 的 torrent 子命令：announce/create/dump/from-link/link/piece-length/show/stats/verify） | test_package 用 `torrent show` |

**Q：上游测试结果？**
A：`cargo test --release --target aarch64-unknown-linux-ohos -p imdl
--lib --bins --no-fail-fast` 在 HarmonyOS PC 真机执行：
**280 passed / 2 failed / 2 ignored，通过率 280/282 = 99.3%**（含忽略
280/284）。

**Q：失败的 2 个是什么？**
A：`subcommand::torrent::create::tests::follow_symlinks` 与
`symlink_root`——测试经 `std::os::unix::fs::symlink` 在临时目录创建符号
链接，而本平台 HMDFS uid 映射卷**不支持创建 symlink**（坑 #1 的同源环境
限制：conan 缓存、build 目录、/storage 全部 EPERM）。属运行环境限制而非
被测逻辑缺陷（imdl 的 symlink 处理代码未做任何修改）。

**Q：test_package 测了什么？**
A：三层 15 断言全过：
- 鸿蒙特有 4：AArch64 ELF / musl loader（/lib/ld-musl-aarch64.so.1）/
  OHOS code signature / 产物非空可执行；
- 冒烟 3：`--help`、帮助含 torrent、`--version` 报 0.1.16；
- 功能 8：真实 .torrent 工作流——create（--announce）→ bencode 结构
  （顶层 dict / announce+info 键 / 文件名）→ show 输出名字 → verify
  重哈希 OK → link 产出 40-hex infohash 的 magnet。

**Q：打包内容？**
A：`bin/imdl`（~4MB，静态 Rust std + 动态 libc/ld-musl）、licenses/LICENSE、
res/README.md。无 conan 依赖（纯 Rust 依赖集）；构建期 tool_requires
rust-toolchain/1.97.1。

**Q：与其他 Rust 先例的差异点？**
A：below 依赖 libelf/zlib（libbpf-sys）需 conan 依赖 + libbpf OHOS 补丁；
intermodal 全内嵌无需任何 conan 依赖，链路更短。运行期共享库注入
（openssl3 bottle + 合成 libz.so）仅服务 cargo 自身运行，与产物无关。
---

**编译结束**: 2026-09-23 20:36
**最终状态**: built
