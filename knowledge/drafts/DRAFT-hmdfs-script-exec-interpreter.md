# DRAFT-hmdfs-script-exec-interpreter：HMDFS/SELinux 沙盒禁止直接执行脚本→解释器执行

> Contributor: librsvg-2.62.3 适配 | Status: Draft | Updated: 2026-08-14
> Source: archives/l/librsvg/2.62.3（继承 2.62.2，本轮复用 + CI 确认）

## 现象

meson 构建中 `find_program('meson/makedef.py', native: true)` 能"找到"脚本文件，
但设备端 $HOME 挂载 HMDFS，沙盒/SELinux **禁止直接执行脚本文件**（.py/.sh），
运行时无法把它作为可执行程序启动。librsvg 的 patch 0001/0002（注释：
`HMDFS workaround: Cannot execute Python scripts directly due to SELinux restrictions`）
把调用方式改为"解释器 + 脚本路径"：

```meson
python3_native = find_program('python3', native: true)
makedef_script = files('meson/makedef.py')
```

## 主从根因（curation-auditor 建议的明确化）

- **主根因**：HMDFS/SELinux 沙盒禁止直接执行脚本文件 → 必须用解释器执行。
- **附加 note（非主根因）**：OHOS 自动签名与并行编译并发冲突，产生
  `Text file busy (os error 26)`，用 `CARGO_BUILD_JOBS=1` / `CARGO_JOBS=1`
  限制并行规避。两者均为平台限制类（归轴1 平台能力边界，深度浅），但机制
  不同，明确主从避免混为一个根因。

## 与现有知识的关系

- E079（HMDFS 硬链接）不覆盖脚本执行限制，二者机制不同。
- 既有"脚本不可直接执行"在本仓 knowledge/graph 无条目，本主题无覆盖。
- 跨库可复用：OHOS 上 meson/make 直接执行 .py/.sh 的集成都会命中此限制。

## 方案

1. `find_program('python3', native: true)` 探测解释器，`files('meson/makedef.py')`
   提供脚本路径，组合成 `[python3_native, makedef_script, ...]` 命令。
2. 并行构建设置 `CARGO_BUILD_JOBS=1` / `CARGO_JOBS=1` 规避签名并发
   `Text file busy (os error 26)`。

## 验证证据

- 2.62.2 实机取证（patch 0001/0002 注释）；本轮 round-4 CI 日志
  `Program python3 found: YES`，解释器路径生效、makedef.py 正常产出，
  CI exit 0，1/1 100%。
- 附加 note 证据：`CARGO_BUILD_JOBS=1` 限制并行后无 `Text file busy (os error 26)`。

## 禁止做法

- 不要直接 `find_program('meson/makedef.py', native: true)` 当可执行文件用——
  HMDFS 沙盒禁止直接执行脚本，运行期必然失败。
