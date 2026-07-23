# mmv

## 简介
mmv 是一个用于移动、复制、追加和链接多个文件的工具，支持通配符模式匹配。它可以安全地批量操作文件，避免误操作。mmv 还可以通过符号链接以 mcp（复制）、mln（链接）、mad（追加）等别名调用，执行对应的文件操作。

## OHOS 适配
- **构建系统**: 使用 autotools（configure + make）
- **shebang 修复 (E165)**: configure 脚本使用 `#! /bin/sh`，OHOS 无 /bin/sh，替换为 `#!/system/bin/sh`
- **umask 修复 (E110)**: configure 中 `umask 077` 在 HMDFS 上导致临时目录权限问题，替换为 `umask 002`
- **构建模式**: 使用 `--build=aarch64-unknown-linux-gnu`（不传 `--host`），native 编译模式使 make check 可正常运行
- **警告禁用**: 使用 `--disable-gcc-warnings` 避免严格警告导致构建失败
- **预生成文件**: Release tarball 已包含预生成的 configure 和 cmdline.c/cmdline.h，无需 bootstrap

## 依赖
- 编译工具: clang, autotools
- 无额外库依赖（源码分析确认 mmv 2.10 未使用 bdw-gc）

## 安装产物
- bin/mmv — 主二进制
- bin/mcp, bin/mln, bin/mad — 通过 install-exec-hook 创建的符号链接（指向 mmv）

## 功能验证
```bash
mmv --version
mmv --help
```

## 参考
- GitHub: https://github.com/rrthomas/mmv
- Homebrew formula: https://github.com/Homebrew/homebrew-core/blob/master/Formula/m/mmv.rb
