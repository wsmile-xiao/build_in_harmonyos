# termbg

## 简介

termbg 是一个用于**终端背景色检测**的 Rust 库，附带一个同名 check program。
检测结果以 RGB 或主题（Dark / Light）形式给出。

## 功能概述

- **终端类型识别**: 支持 xterm 兼容终端、GNU Screen、tmux、Win32 console 等
- **背景色检测**: xterm 控制序列查询（OSC 11）或 Win32 API；两者失败时回退到
  `COLORFGBG` 环境变量
- **主题判定**: 检测到的 RGB 转 YCbCr，Y > 0.5 判为 light，否则 dark

## 产物

| 产物 | 说明 |
|---|---|
| `bin/termbg` | 上游自带的 check program：打印终端类型 / 背景 RGB / 主题 |

## 使用

```console
$ termbg
Check terminal background color
  Term : Tmux
  Color: R=0, G=0, B=0
  Theme: Dark
```

## OHOS 适配

### 适配要点

- **构建系统**: cargo（`Cargo.toml` 的 `build = false`，无 `build.rs`）
- **编译命令**: `cargo build --release --locked --target aarch64-unknown-linux-ohos`
- **工具链**: 制品仓基础设施包 `rust-toolchain/1.97.1`（tool_requires）；不使用
  rustup（标准 rustup 无法识别 HarmonyOS 宿主）
- **工具链签名**: 包内 cargo/rustc/librustc_driver 无 code signature，OHOS 拒绝
  execve → `binary-sign-tool -selfSign 1` 自签名私有副本，保持
  `<root>/bin` + `<root>/lib/rustlib` 的 sysroot 布局
- **cargo 运行库**: cargo 动态链接 libssl/libcrypto（OpenSSL 3.x 符号），系统
  OpenSSL 3.0 缺符号 → Harmonybrew OHOS bottle + `LD_LIBRARY_PATH` 前置
- **依赖源**: crates.io 直连在设备上不可靠 → `rsproxy.cn` sparse 镜像 + CA bundle
- **上游源码零改动**: 无任何补丁，适配全部发生在构建环境层

### 测试

- 上游：`src/lib.rs` 的 `#[cfg(test)] mod tests`，6 个用例，设备实测 6/6 通过
- 消费者 + 鸿蒙特有：`test_package/test_termbg.py`，12 条断言
