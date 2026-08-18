# acf-freeradius3 0.3.1 适配笔记

## 项目简介
acf-freeradius3—— Alpine Configuration Framework (ACF) 的 FreeRADIUS
配置模块（纯 Lua + HTML .lsp 模板，无 C 编译）。上游
gitlab.alpinelinux.org/acf/acf-freeradius3，GPL-2.0。

## 依赖
- **acf-core/0.24.1**（制品仓已发布，ACF 框架 mvc.lua 分发，同 acf-apk-tools 先例）

## 构建与适配
1. **make 构建**：`make all` 是 no-op（校验 Makefile 语法），`make install
   DESTDIR=<pkg>` 复制 Lua/HTML 到 `<pkg>/usr/share/acf/app/freeradius3`；
2. **源码获取用 git clone**：GitLab archive 端点(/-/archive/)被反爬 418
   拦截，但 git 智能 HTTP 端点可用——conandata 存 git URL + branch v0.3.1，
   source() git clone（R39 官方源保留）;
3. **package_info**：resdirs=usr/share/acf/app/freeradius3（供 acf-core 分发），
   bindirs 置空（纯 Lua 模块）。

## 验证
- 模拟 CI 干净 PATH conan create（--build=missing, ohos-aarch64 profile）。
