# keychain 2.9.8 适配笔记
## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-07-02
- 状态: built
## 编译步骤
keychain 是 SSH/GPG key agent 管理器，使用 Bourne shell 脚本实现。
1. **init-build**: 下载并解压源码
2. **make PREFIX=...**: 构建 keychain 脚本、man page
3. **手动安装**: bin/keychain, share/man/man1/keychain.1, share/bash-completion/completions/keychain.bash
4. **Staging 验证**: bash -n 语法检查通过，版本号 2.9.8 嵌入正确
## 遇到的问题
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | autoconf 未安装 | 从 cmd-pkgs 安装 autoconf 2.72 |
| 2 | Conan source() SSL 失败 | fallback 到本地归档 tarball |
| 3 | conanfile.py 模板假设 autotools | 重写为 plain make |
| 4 | test_package 使用 Conan 1.x API | 改用 Conan 2.x |
## 验证结果
G0-G4 + L2/L4/L5: 全部 PASS
**最终状态**: built
