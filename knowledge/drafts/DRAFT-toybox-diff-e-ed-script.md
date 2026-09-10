# toybox diff 缺 `-e`（ed 脚本）输出 — 核心路径依赖 `diff -e` 的脚本必须让 GNU diffutils 先于 toybox 出现在 PATH

> Draft: DRAFT-TOYBOX-DIFF-E-ED-SCRIPT
> Stem: `toybox-diff-e-ed-script` — pairs with the same-stem `.kv`（doc_file 指向本文件）

## 基本信息

- **ID**: DRAFT-TOYBOX-DIFF-E-ED-SCRIPT
- **严重度**: 2
- **类别**: platform-userland-gap
- **触发工具**: toybox|diff|-e|ed|diffutils|changetrack|GNU diff
- **阶段**: testing|runtime-environment
- **principles**: P013（平台限制必须降级而非绕过）
- **similar_to**: [E402, E010, E098]（OHOS toybox 命令能力差异族：gzip 长选项 / sed+expr / 缺 install——同族不同机理，无覆盖）

## 错误特征

```
diff: Unknown option 'e' (see "diff --help")   # toybox 遮蔽时的 stderr；stdout 为空
Can't do diff -e:$!                            # 仅当 diff 完全不可执行时才触发（罕见路径）
```

## 可复现问题（自包含双探针）

```bash
printf 'a\nb\nc\n' > o; printf 'a\nX\nc\n' > n
diff -e o n
# ambient=toybox 0.8.12（/usr/bin/diff）: "diff: Unknown option 'e' (see \"diff --help\")"，rc=2，stdout 为空
PATH=/data/service/hnp/bin:$PATH diff -e o n
# GNU diffutils 3.10（设备工具链用户态目录）: 输出 "2c"/"X"/"."，rc=1
# PATH 前置即修复（与 CI profile buildenv 的 [buildenv] PATH 同语义）
```

changetrack 4.7 的变更检测核心路径以管道 `open(DIFF, "diff -e ...")`（源码 L341）调用 diff。
默认 PATH 下解析到 toybox diff 时**不是 die，而是静默产出空 ed 脚本**：open 成功、diff 向
stderr 报错、管道 stdout 为空，changetrack 收集到空 @ed 并写出空的 `.ed` 恢复脚本——变更
日志仍有记录，恢复路径静默损坏。`die "Can't do diff -e:$!"` 仅在 diff 完全不可执行时触发。

## 根因分析

toybox（0.8.12）diff 只实现 -u/-c 风格输出；`-e`（ed 命令输出，用于生成可回放的编辑脚本）
不在其支持范围。失败点机理链：**环境 PATH 解析 `diff` → 命中 toybox → `-e` 不识别 →
stderr 报错 + stdout 为空 → 消费方拿到静默空 ed 脚本**（而非显式失败）。设备默认 PATH 中
`/usr/bin`（toybox）先于携带 GNU diffutils 3.10（archives/d/diffutils）的工具链用户态目录，
因此凡从环境 PATH 解析 `diff` 的脚本都会静默拿到功能受限的实现。

## 影响面

任何以 `diff -e` 为核心路径的脚本/工具（changetrack 4.7 已实证；配置监控/恢复类工具常见；
未来 `diff --ed` / `patch -e` 消费链同样暴露）。普通 `diff` / `diff -u` 消费方不受影响
（toybox 支持）。

## 推荐处置

运行此类消费方时保证 PATH 中 GNU 用户态目录（提供 GNU diffutils）先于 /usr/bin；
Conan test_package 内用 profile buildenv（`env="conanbuild"`，其 PATH 已前置该目录）执行。
测试断言落在 ed 脚本内容上（如包含 hunk 头 `2c`），使 toybox 遮蔽时测试响亮失败而非静默
通过。PATH 前置优先于改补丁（对齐 principles P013：平台限制降级而非绕过——fallback 的
`-u` 降级即此语义）。

## 禁忌

- 在交付文件中硬编码设备私有绝对 diffutils 路径（不可重定位；verification_cmd 中的绝对路径
  仅用于人工复现探针，不入交付配方）
- 替换系统 toybox 或在包内捆绑影子 diff 二进制（系统冲突，R26）

## 关联

- archives/d/diffutils（3.10，提供 GNU diff -e）
- archives/c/changetrack/4.7（已实证消费方）
