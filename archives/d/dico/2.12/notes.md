# dico 2.12 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-14}
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
---

**编译结束**: 2026-09-14 07:01
**最终状态**: built

## 整改（2026-09-14，GLM-8；对应审查 rule4 驳回"解决后真实执行上游测试"）

### 配方改造（build() 接入上游 autotest 套件，真实执行）
- `make -k check MAKEINFO=true SHELL=/bin/sh CPPFLAGS=-I<src>/libltdl` 写入 build()（env=conanbuild）；输出落盘 upstream-check.log 后解析汇总
- 移除 `--disable-shared --enable-static`：上游 dicod 套件经 libltdl 动态加载 mod_LTLIBRARIES（echo 等），纯静态构建 22 个 dicod 用例全挂 "cannot load module"（实测）；dico 为应用非系统同名库，shared 不触发 R26
- 解析器带交叉校验（逐用例 FAILED 数 vs 套件声明失败数），不一致即 raise，防静默漏报；预期限制清单按用例文件名（epp.at/ppexit.at）匹配

### 上游测试新账本（2026-09-14 真机实测，权威轮 conan create RC=0）
- 运行注册口径（configure 后各 suite）：wordsplit 190 + lib 38 + grecs 42 + dicod 23 + modules 66 = **359**
- **通过 357，test_skipped 2，未预期失败 0**
- test_skipped 逐项：`epp.at#28`（External preprocessor）与 `ppexit.at#29`（Exit status）——stderr 空值断言被 bash `shell-init: getcwd` 污染行打破（E386 同族 HMDFS 假阴性，用例本体功能正常；原始 diff 见 upstream-check.log）
- 源文件级口径 141 个 .at（与审查脚本静态计数一致）；两口径关系见 PR 正文补充说明
- 消费者测试 N_consumer = 1（test_package/test_dico.py，3 断言，全过）
