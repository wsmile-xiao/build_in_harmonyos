# acf-asterisk 0.7.0 适配笔记

## 项目简介
acf-asterisk—— Alpine Configuration Framework (ACF) 的 Asterisk 配置
模块（纯 Lua + HTML .lsp 模板，无 C 编译，make 构建）。上游
gitlab.alpinelinux.org/acf/acf-asterisk，GPL-2.0。

## 依赖
- **acf-core/0.24.1**（制品仓已发布，ACF 框架 mvc.lua 分发，同 acf-apk-tools 先例）

## 构建与适配（同 acf-freeradius3 先例）
1. make all no-op 校验 + make install DESTDIR=<pkg> 复制到
   usr/share/acf/app/asterisk；
2. 源码用 git clone（GitLab archive 端点 418 反爬拦截，git 智能 HTTP 可用）；
3. package_info: resdirs=usr/share/acf/app/asterisk，bindirs 置空。

## 验证
- 模拟 CI 干净 PATH conan create（--build=missing, ohos-aarch64 profile）。
