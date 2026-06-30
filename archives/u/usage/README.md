# usage — OpenHarmony 编译记录

## 基本信息
- 软件: usage (usage-cli)
- 版本: 3.4.0
- 描述: A specification for CLIs — CLI usage definition language
- 构建系统: custom (Rust/Cargo)
- 目标: ohos-aarch64
- 源码: https://github.com/jdx/usage (Rust project by jdx)

## 编译指导

### 注意事项
- Rust 项目，使用 cargo build --release 编译
- 源码从 crates.io 下载更稳定 (中国大陆)
- init-build 可能误检测为 autotools，需手动修正 manifest.yaml 中 build_system
- doc-tests 在 OpenHarmony 因 E051 可能失败 (不阻塞编译)