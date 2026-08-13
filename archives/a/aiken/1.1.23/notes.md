# aiken 1.1.23 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-08-08}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI conan create 失败: `linker 'cc' not found` | CI worker PATH 只有 `clang`，没有 `cc`/`gcc` 符号链接；rustc 默认用 `cc` 链接 build script 与产物 | generate() 写 `.cargo/config.toml` 指定 `[target.aarch64-unknown-linux-ohos] linker="clang"`；build() 将 clang 以 `cc`/`gcc` 名字软链到临时目录并置入 PATH（兜底直接调 `cc` 的 C build script） |
| 2 | CI conan create 3600s 超时 | cargo 链接失败后等并行任务，且 aiken 工作区（tokio/reqwest/icu/lalrpop 等）全量 release 编译耗时长 | 在 ci/config/build_timeouts.txt 将 aiken/1.1.23 超时上调至 10800s |

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

**编译结束**: 2026-08-08 21:46
**最终状态**: built
