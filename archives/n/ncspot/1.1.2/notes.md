# ncspot 1.1.2 适配笔记

## 编译环境
- 构建系统: cargo (Rust项目)
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (Rust 1.95.0)
- 状态: published

## 编译步骤

1. 下载源码: https://github.com/hrkfdn/ncspot/archive/refs/tags/v1.1.2.tar.gz
2. 安装依赖: alsa-lib 1.2.12 (cmd-pkgs), portaudio 19.7.0 (已有), openssl 3.5.6 (已有)
3. cargo build --release --no-default-features --features "portaudio_backend,crossterm_backend"
4. 手动安装二进制到staging目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | nix crate v0.23.2编译失败 | nix依赖libc符号在musl上缺失(O_FSYNC/mq_open/shm_open等) | 改用portaudio_backend避开alsa→nix依赖链 |
| 2 | pulseaudio_backend不可用 | OHOS上无libpulse库 | 使用portaudio_backend替代 |
| 3 | SSL证书问题导致cargo下载失败 | musl libc缺少CA证书 | 安装CA证书到~/usr/local/ssl/cert.pem |

## 依赖版本

- Rust: 1.95.0
- portaudio: 19.7.0
- openssl: 3.5.6
- alsa-lib: 1.2.12 (installed but not used in final build)
- ncurses: 6.5 (available but not used - crossterm is pure Rust)

## 验证结果

```bash
ncspot --version
# ncspot 1.1.2
```

## 注意事项

- ncspot是Spotify客户端，实际使用需要Spotify账号认证
- 使用portaudio_backend而非默认pulseaudio_backend
- 使用crossterm_backend而非ncurses_backend（纯Rust实现，更稳定）
---

**编译结束**: 2026-06-17 23:44
**最终状态**: published
