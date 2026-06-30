# mask 0.11.7 — 适配笔记

## 编译信息
- **构建系统**: cargo (Rust)
- **版本**: 0.11.7
- **编译命令**: `cargo build --release`
- **安装方式**: 手动复制 `target/release/mask` 到 `$TEST_PREFIX/bin/mask` 和 `$DEFAULT_PREFIX/bin/mask`
- **源码来源**: crates.io 注册表 (cargo 缓存)，非 GitHub tarball

## 编译过程
1. 使用 cargo search/info 找到 mask crate 版本 0.11.7
2. 使用 cargo install mask --version 0.11.7 首次编译（验证可行性）
3. 在源码目录执行 `cargo build --release` 正式编译
4. 手动安装二进制到 DESTDIR 和本地前缀
5. cargo test 运行测试 - 部分测试因 ANSI 颜色码环境差异失败，不影响功能

## 关键问题与修复

### 问题1: GitHub 下载 URL 不可用
- mask 的 GitHub releases 没有 tag tarball (404)
- 修复: 使用 crates.io 注册表源码 (cargo 缓存)，创建本地 tarball

### 问题2: 构建系统识别错误
- init-build 默认检测为 autotools，但 mask 是 Rust/cargo 项目
- 修复: manifest.yaml 中设置 `build_system: cargo`

### 问题3: cargo test 部分失败
- 单元测试: reads_root_maskfile 期望 ../maskfile.md 但源码目录缺少该文件
- 集成测试: ANSI 颜色码与测试断言不匹配 (CLICOLOR_FORCE)
- 结论: 非功能性 bug，binary 功能正常

### 问题4: G0 干净构建验证
- clean_verify 不支持 cargo 构建系统（仅支持 configure + make）
- 修复: 手动验证 cargo build --release 可重复构建成功

## 知识提取
- E200: Rust项目使用cargo编译而非autotools (已记录到知识图谱草稿)

**编译结束**: 2026-06-11 02:47
**最终状态**: built
---

**编译结束**: 2026-06-11 02:53
**最终状态**: built
