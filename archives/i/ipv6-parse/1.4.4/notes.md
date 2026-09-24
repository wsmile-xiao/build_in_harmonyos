# ipv6-parse 1.4.4 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-22}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

## 语言判定记录（R47 lang-preflight 覆盖说明）

- 工具 lang-preflight 依据 manifest 优先（package.json 存在 main/scripts/engines → nodejs）判为 env_unsupported（nodejs，源文件 27 个 nodejs:16 c:8 bash:6 python:3）。
- 证据链显示主体为 C 库：
  1. README 标题: "IPv6 / IPv4 address parser in C"，Distribution Methods 含 NPM/WASM/Linux 包/Homebrew/Conan/vcpkg/CMake，NPM 只是发行渠道之一；
  2. 上游自带 conanfile.py（name=ipv6-parse，settings.rm_safe compiler.libcxx/cppstd 纯 C 配置）与 test_package/；
  3. CMakeLists.txt: project(ipv6 C) + add_library(ipv6-parse) + install(TARGETS) + pkg-config .pc.in；
  4. 附带 vcpkg/portfile、debian/、Formula/ipv6-parse.rb、ipv6-parse.spec 全套 C 库发行渠道；
  5. 计入 nodejs 的 16 个文件里 index.js 只是加载 WASM 的 Node 绑定入口，docs/ipv6-parse.js（1357 行）为 emscripten 生成胶水，docs/ipv6-parse-api.* 为 API 包装，test/*.js 与 eslint.config.js 为绑定测试/辅助脚本；主体逻辑全在 ipv6.c（1217 行）。
- 按 SKILL 边界规则“辅助脚本不算主体语言”，判定 detected=c（c↔cpp 兼容族，任务 expected=cpp 不触发迁移），覆盖 env_unsupported，继续 C 适配。
- 证据留存：源码目录 /storage/Users/currentUser/tmp/builds/ipv6-parse-1.4.4.work（tarball sha256 fa3062c695982c6ecfb2c85a013b9e4175e8afaba3b9602ef49bf30cb9e81d90，上游 tag v1.4.4 commit 22f64c40661ebb8c4377e08f8db5c3ff43b0b6f1）。
---

**编译结束**: 2026-09-22 17:30
**最终状态**: built

## 知识查重与路径判定（knowledge_decision）

- 候选材料：本库适配中唯一非平凡经验是 lang-preflight 将「纯 C 库 + 根级 npm/WASM 绑定 manifest」误判为 nodejs → env_unsupported 假终态；经证据链（README 标题、CMake project(ipv6 C)、上游 conanfile.py、vcpkg/debian/Formula 发行渠道、ipv6.c 1217 行主体）判定为 c/cpp，跳过该假门禁继续。真实构建/测试/Conan 均无首错、无补丁、无新增可复用适配问题。
- 快照扫描范围：knowledge/graph/（542 kv + 540 md，index.tsv）+ knowledge/drafts/ 全量。
- 等价命中（逐字段比对）：DRAFT-E586（libyal lang-preflight 假信号家族）、DRAFT-E592（libyal 根级 PEP517 manifest → mixed 误判）与本例属同一知识家族：
  - error_signature：`语言不匹配: task=cpp, detected=nodejs/mixed` 一致（本例 detected=nodejs，E586/E592 为 mixed，同根因不同出口）；
  - root_cause：lang_detect manifest 优先级将绑定/打包 manifest（package.json / pyproject.toml）排在 C/C++ 构建系统（CMakeLists / configure.ac）之前 一致；
  - 触发条件：根级绑定 manifest + C/C++ 主体 一致；
  - 方案：按 R47 边界规则「辅助脚本/绑定不算主体」人工复核后判 c/cpp 继续 一致；
  - 验证：主体源码占比与构建入口复核 一致。
- knowledge_decision: reuse_existing（走路径 A）。理由：等价命中既有草稿家族；且该知识本质属共享框架（lang_detect）缺陷面，按规则「共享框架…永远不能走路径 B」。本轮未创建任何 DRAFT 草稿对。
- 依赖项分类：无（0 依赖）。
- issue_action: none（任务固定）。
