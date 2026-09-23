# E557 — HarmonyOS toybox gzip 解压仅识别 .gz 后缀：脚本 .tgz/.tar.z 解压失败

> Contributor: HouYuxuan | Status: Draft | Updated: 2026-09-08
> Source: PR #8957 feat(comprez): 2.7.3 适配 HarmonyOS PC（z 工具运行时解压 .tgz）

## 背景

comprez（上游项目 z）是纯 shell 脚本压缩/解压前端。脚本解压 `.tgz` 时
先把文件改名 `.tar.z` 再调用 `gzip -d`。HarmonyOS gzip 为 **toybox 0.8.12**，
`gzip -d` 仅识别 `.gz` 后缀文件名，对 `.tar.z` 报 `gzip: no .gz` 拒绝解压；
且 toybox gzip **不支持 `-S` 选项**改后缀，无法用 GNU gzip 的 `-S .z` 方案。

> 与 E402（toybox gzip 仅支持长选项 --force/--best 失败）同族：E402 覆盖
> "安装/man 压缩场景的长选项差异"，本条目覆盖"运行时解压场景的后缀识别差异"，
> 错误签名、触发阶段、修复方案均不同，参照 E010/E098/E188 同族独立条目先例。

## 错误特征

```text
gzip: no .gz: dir.tar.z
z: cannot defeather dir.tar.z
```

## 触发条件

- 构建系统: 任意（纯 shell 脚本，无编译）
- 阶段: runtime（脚本解压 .tgz/.tar.z 时调用 gzip -d）
- 环境: HarmonyOS（gzip 为 toybox 0.8.12）

## 根因分析

GNU gzip 的 `-d` 支持 `.gz`/`.z`/`-z` 等多种后缀，而 toybox 精简实现只认
`.gz`。脚本（z 工具）解压 `.tgz` 时按传统习惯改名 `.tar.z` 再调用
`gzip -d -n file.tar.z`，toybox 因后缀不匹配直接拒绝，且 `-S` 选项不受支持，
无法用改后缀参数规避。

## 解决方案

### 推荐方案

解压调用改用 stdout 管道输出（`-c`），toybox 管道模式不检查输入文件后缀：

```sh
if $ucommand -c "$arg" > "$tarf" 2>/dev/null
then
    rm -f "$arg"
else
    rm -f "$tarf"
    $ucommand "$arg"     # 回退原命令（GNU gzip 等）
fi
```

### 禁止做法

- ❌ 直接 `gzip -d -n file.tar.z`（toybox 只认 .gz 后缀，必然失败）
- ❌ 依赖 `gzip -S .z`（toybox 不支持 -S 选项）

## 验证

```bash
cp x.tgz x.tar.z
gzip -d -n -c x.tar.z > out.tar && echo OK
tar -tf out.tar | head -3
```

## 关联条目

- 相关: E402（同族：toybox gzip 长选项差异）
