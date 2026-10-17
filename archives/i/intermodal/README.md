# intermodal

> 📦 A 40' shipping container for the internet — BitTorrent 元信息 CLI 工具（二进制 `imdl`）

- 上游：https://github.com/casey/intermodal（Casey Rodarmor）
- 许可：CC0-1.0
- 语言：Rust（edition 2021，纯 Rust 依赖集，无 C 绑定）

## 功能

对 BitTorrent 元信息文件的完整 CLI 闭环（无网络即可用）：

- `imdl torrent create` — 从文件/目录创建 .torrent（可 --announce 指定 tracker、
  自定义 piece length 等）
- `imdl torrent show` — 渲染人类可读的元信息
- `imdl torrent verify` — 重哈希校验数据与 .torrent 一致
- `imdl torrent link` — 生成 magnet link（40-hex infohash）
- `imdl torrent stats` — 统计一批 .torrent 文件

## 适配说明（0.1.16，OHOS PC aarch64）

- 构建方式：cargo 原生构建（构建期 tool_requires `rust-toolchain/1.97.1`，
  宿主=目标=aarch64-unknown-linux-ohos），产物 `bin/imdl` 已用
  binary-sign-tool 自签名（HarmonyOS 拒绝执行未签名 ELF）。
- 上游测试：`cargo test -p imdl --lib --bins` 于 HarmonyOS PC 真机执行，
  280 通过 / 2 失败（HMDFS 不支持创建 symlink 的环境限制）/ 2 忽略。
- 详细踩坑记录见 `0.1.16/notes.md`。
