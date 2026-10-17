# libinjection 3.9.2 适配笔记

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
## 知识判定（knowledge_decision: reuse_existing → 路径 A, 2026-09-22）

快照: /storage/Users/currentUser/tianyi/knowledge-snapshot-libinjection-3.9.2-r01
- repository: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git
- ref: main, HEAD 48d9cee6844d0fca1f25e86c2df1293b904855d8, sparse: knowledge

候选与逐字段比对（error_signature / root_cause / rec_approach 一致 → 等价命中）：
1. 上游源码生成脚本为 Python2 语法（print 语句/iterkeys）→ 命中 E269
   （error_signature `SyntaxError: Missing parentheses in call to print` 匹配；
   root_cause "Python 2 语法在 Python 3 环境无法执行" 一致；rec_approach port-python-script 一致）
2. codeload tar.gz URL 无扩展名 → BadZipFile（conan get() 编码器误选）→ 命中 E276/E483/E392
   （error_signature `BadZipFile: File is not a zip file`, root_cause 一致；
   rec_approach explicit-filename-in-get 一致，本轮已用 conandata.yml filename 键落地）
3. raw makefile 配方三陷阱（make 默认 cwd 错、install 目标在子目录）→ 命中 E392/E097
   （error_signature `No targets specified.*No makefile found`、`No rule to make target.*install` 匹配；
   rec_approach raw-makefile-conan-recipe-pattern 一致，本轮已用 cwd=source_folder + src 子目录 make install 落地）
4. clang -Wstrict-prototypes（无原型函数声明）→ 命中 DRAFT-asmotor-1.0.0-knr-strict-prototypes-c99
   （error_signature `function declaration without a prototype is deprecated.*\[-Werror,-Wstrict-prototypes\]`
   完全匹配；root_cause 一致；本轮按草稿 fallback 现代化路线补 void 原型）
5. lang-preflight 绑定目录误判（共享框架 scripts/ 行为）→ 不沉淀草稿（共享框架不得走路径 B），
   已在本地做最小可逆临时修复并恢复零 diff（见隔离审计）

无新增知识价值 → 不创建工作树 knowledge/drafts/ 草稿；knowledge_decision: reuse_existing；路径 A。
---

**编译结束**: 2026-09-26 20:18
**最终状态**: published

## R02 知识复核（knowledge_decision: reuse_existing → 路径 A, 2026-09-26）

快照（复用 R01 外置只读快照）: /storage/Users/currentUser/tianyi/knowledge-snapshot-libinjection-3.9.2-r01
- repository: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git
- ref: main, HEAD 48d9cee6844d0fca1f25e86c2df1293b904855d8, sparse: knowledge（只读审计通过，无写入）

R02 新候选（CI L1 首错：`env: exec python: No such file or directory` → exit 127，
上游生成脚本 shebang `#!/usr/bin/env python` 在受控构建环境仅 python3 无 python）逐字段比对：
- 命中 E049（shebang 硬编码/解释器解析，error_signature `shebang.*hardcoded.*path|interpreter.*not found.*shebang`，
  rec_approach shebang-portable-fix 一致）
- 同族命中 E269（Python2 脚本在 Python3 环境，R01 已引用）、E143（shebang+env 修复，`/usr/bin/python3: no such file` 同族）
- 本轮修复落地：3 个生成脚本 shebang 改 python3（补丁 0002/0003/0005）+ recipe 受控解释器解析
  （build() 内建立 .ohos-python-bin python→python3 链接并前置 PATH，随构建清理）
- 无新的非等价候选 → 不创建草稿；knowledge_decision: reuse_existing；路径 A（复核结论与 R01 一致）
