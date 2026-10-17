# nift (nifty-site-manager)

Nift（aka nsm / nifty-site-manager）是跨平台静态网站生成器，使用 C++ 编写，
自包含构建（内嵌 Lua-5.3/LuaJIT、exprtk、rapidjson、hashtk），无第三方依赖。

- **官网**: https://github.com/nifty-site-manager/nsm
- **许可证**: MIT
- **分类**: 静态网站生成器 / web 工具

## 软件描述

- 模板/脚本驱动的静态站点生成（SSI、Lua、ExprTk、逻辑/变量等）
- 命令行 `nift` / `nsm` 双入口（同一二进制，nsm 为原名）
- 站点初始化：`nift init` / `nift init-html`（后者直接构建最小可运行站点）
- 增量构建、watcher、Git 集成、分页等

## 适配说明（OHOS aarch64）

- **构建系统**: 纯 Makefile（无 configure 脚本）
- **编译方式**: `make CC=clang CXX=clang++ LUA_VERSION=5.3 -jN`
  - Makefile 默认分支编译内嵌 LuaJIT；显式 `LUA_VERSION=5.3` 切换到内嵌
    Lua-5.3 的 `generic` 目标，规避 LuaJIT 子构建在 OHOS 上的额外适配成本
  - Lua-5.3 子 Makefile 硬编码 `CC= gcc`，需把 CC/CXX 放最外层 make 命令行
    （经 MAKEFLAGS 传播到子 make）覆盖
  - 可选环境覆盖：`NIFT_OPT`（默认沿用上游 -O3；受限机器可用 -O0/-O1）、
    `NIFT_JOBS`（默认 min(cpu,8)）
- **打包**: 上游 install 依赖 `chmod`（HMDFS E046 下会失败），配方 package()
  直接 copy `nsm`/`nift` 到包内 `bin/`，语义等价、不依赖 chmod
- **依赖**: 无 conan 外部依赖；运行时仅依赖系统 libc / libc++_shared.so
- **测试**: 上游无测试套件（无 check/test 目标）；test_package 补全 11 项
  消费者功能断言（test_package/test_nift.sh），全部真实执行打包二进制：
  `--version`、`init-html` 构建与静态资源镜像、`track`+自定义模板+`build`
  站点生成 E2E（模板变量 $[title]/@content/多页面）、增量构建（hash 模式）、
  内嵌 Lua `nift run`、`nift init`

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 3.0.3 | built | 2026-09-04 | 官方 tag v3.0.3；conan-verify 全门禁 PASS；W3 本地 CI（build_and_test.sh）通过，.ci-result.json exit_code=0 |
