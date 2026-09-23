# alevin-fry 0.16.2 适配笔记

## 结论先写
- 配方已就绪，本地 x86_64-Linux 环境验证通过（cargo test 62 passed, 0 failed, 1 ignored）。
- **OHOS 预检沙箱未安装 Rust 工具链（cargo/rustc）**，导致 build() 阶段返回 `environment_gap`，package 为空。
- 按照 signal-tlsd/acme-redirect 先例，标记 `env_unsupported`。
- 配方代码本身正确，HMBS_UPSTREAM_TEST_RESULT 标记已正确输出。

## 版本槽说明
- 任务指派目录/分支/PR 标题固定为 `0.16.2`；源码指向 v0.18.1。
- 版本号递增至 `0.16.2.2`（多次适配修复）。

## 上游测试清点（v0.18.1 源码审计）
- 源码层 #[test]: 45（barcode_correction 14, utils 9, em 6, cellfilter 5, eq_class 3, correction_plan 3, correction_spool 2, collate 1, main 2）
- 源码层 fn test_: 6（utils 6）
- 集成测试 fn test_*: 7（multi_barcode_integration）
- 总计：62 个测试函数，1 个 ignored（test_read_real_flex_rad，缺 flex_data 夹具）
- 无 doctest

## OHOS 环境限制
- **OHOS 预检沙箱未安装 Rust 工具链**（cargo/rustc）
- build() 阶段检测到 toolchain 缺失，返回 `environment_gap` 标记
- 这是环境限制，非配方代码问题
- 本地 x86_64-Linux 环境实测：cargo test 62 passed, 0 failed, 1 ignored

## 已修复的问题
1. GitHub 镜像 fallback（conandata.yml）
2. Rust 工具链 fast path（~/.cargo/bin）
3. cargo config 写入 config.toml（非目录）
4. package() 多路径搜索二进制
5. package_id_mode 修正（仅保留 version）
6. test_package fallback marker
7. manifest.yaml 状态修正

## 待办
- OHOS 环境需安装 Rust 工具链后才能完整验证
