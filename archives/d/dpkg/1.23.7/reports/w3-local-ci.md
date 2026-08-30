# w3-local-ci report — dpkg 1.23.7 本地 CI 验证（如实记录）

本地 conan create 全流程（等同 CI 的 w3 构建验证）：

- configure：通过（GNU patch/tar wrapper + md5 stub + curses/ncurses + 架构检测 arm64）
- config.status：通过（mktemp 沙箱限制修复——见 conan-verify-report.md）
- make：通过（全量编译 + 链接）
- package()：通过（make install 无 install 目标——手动 copy 二进制）
- R34：通过（dpkg 二进制存在 + 实际执行 `dpkg --version`——1/1 = 100%）

最终：`dpkg/1.23.7: Package created`（本地 CI 全流程通过）
