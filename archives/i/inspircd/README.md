# inspircd

Modular high-performance Internet Relay Chat (IRCv3) server daemon (C++17).

- 上游：https://github.com/inspircd/inspircd（官网 https://www.inspircd.org/）
- 构建：perl `Configure` + `make`（`tool_requires perl/5.42.2`），`--disable-auto-extras` 关闭全部依赖型 extra 模块，核心零外部依赖
- 产物：`bin/inspircd` + `modules/*.so`（core 模块启动时自动加载）
- 上游无自动化测试（外部 irctest harness 仅）；test_package 以最小配置启动真实服务器并完成 IRC 握手（NICK/USER → 001）验证

## 版本

- 4.7.0：首个适配版本（路径 A 基础适配）
