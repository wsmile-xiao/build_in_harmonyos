# glpk 5.0 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出动态 libglpk.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

---

## 附：与本目录 patches/ 的关系

`patches/0001-config.guess.patch` 与 `0002-config.sub.patch` 是**早期源码构建**时期的产物
（给 config.guess/config.sub 加 HarmonyOS 识别分支）。

**本 conan 配方不使用它们**（`conandata.yml` 的 `patches: {}`）——改为在 configure 时显式给出
`--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`，
`build == host` 让 configure 走原生路径、**直接跳过 config.guess**，无需打补丁。
补丁文件保留作为历史记录，供仍走源码构建路线的人参考。

<details>
<summary>早期源码构建记录（存档）</summary>

# glpk 5.0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-05-26}
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

**编译结束**: 2026-05-26 19:15
**最终状态**: published

</details>
