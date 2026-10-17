# 草稿 — OHOS SDK sysroot 已内置 linux/uinput.h 全套 UAPI：uinput/evdev 类库零补丁可编译

> Status: **Draft**（待审核 promote）| severity: `3` | category: `platform, headers, ohos, input` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libuinputplus-0.1.4-ohos-sysroot-uinput-uapi-available.kv`

## 可复现症状与稳定错误签名

- 本条为**平台能力实证**（预防性知识）。对应的预期错误签名（出现时说明另有根因）：
  `fatal error: 'linux/uinput.h' file not found` / `'linux/input.h'` / `'linux/input-event-codes.h'`

## 根因与最小复现

- 实证环境：DevEco OHOS SDK sysroot（API 26，26.0.0.105，与 CI worker 的 ohos-sdk 26.0.0.18 同大版本）。
- `usr/include/linux/` 下 `uinput.h`、`input.h`、`input-event-codes.h` 齐备；`uinput.h` 含 `struct uinput_setup`、`struct uinput_abs_setup`、`UI_DEV_SETUP`、`UI_ABS_SETUP`、`UI_SET_{EV,KEY,REL,ABS,PROP}BIT`、`UI_DEV_CREATE`（Linux 4.4+ UAPI 全套）。
- musl 覆盖 uinput 类库全部系统调用：`open/ioctl/close/write/read/usleep`。
- 双实证：libevdev 1.13.7（input.h/input-event-codes.h，已合入归档）与 libuinputplus 0.1.4（uinput.h，本次真机 shadow CI exit 0，源码零补丁）。
- 若迁移中真出现缺头报错：优先怀疑 sysroot 版本过旧或 `--sysroot`/include 路径配置错误，**而不是**平台缺头。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 假设缺内核头、预置补丁/软链（libevdev 曾为 meson 平台探测做过 harmonyos 软链，那是 meson `host_machine.system()` 探测问题，不是缺头） | 对 CMake 直连 `#include <linux/uinput.h>` 的库不需要 |
| 直接用 sysroot 头编译（采纳） | libuinputplus 0.1.4 三源文件 + 消费测试零补丁通过；W0 结论记“仅 sysroot UAPI 头，无第三方依赖” |

## 最终方案、输入输出与真实验证

- 输入：上游源码原样 `#include <linux/uinput.h>`。
- 处理：无补丁、无额外 requires。
- 输出：`libuInputPlus.so`（AArch64 OHOS ELF）+ 消费测试。
- 真实验证：本机 OHOS clang 交叉编译通过；真机 shadow CI r5 exit 0（L0/L1/L4/L5 pass，40/40 断言）。

## 适用范围、反例、解除条件与风险

- 适用：依赖 Linux 输入子系统 UAPI 的库/工具——libuinputplus、libevdev 已实证；ydotool、wtype、dotool、evtest、input-remapper 等迁移时可先跑 verification_cmd 再决策。
- 反例：glibc 专属头（argp.h 等，见 E169）确实缺失——UAPI 头在 ≠ 所有 Linux 头都在。
- 解除条件：无（能力只会随 SDK 演进增强）。
- 风险（R40）：编译通过 ≠ 适配完成。`/dev/uinput` 节点存在性、普通用户打开权限、ioctl 实际被内核接受，属真机运行层验证，需在设备空闲窗口用最小探针单独确认，与编译层结论分开记录。

## 知识库查重与新增价值

- grep 知识图谱与草稿：无任何 uinput/UAPI 条目；libevdev 归档的 harmonyos 软链是其 meson 平台探测特例。
- 新增价值：①首次沉淀“uinput UAPI 在 OHOS sysroot 齐备”的平台事实与一步验证命令，避免后来者重复探测或预置无用补丁；②明确编译层（已实证）与运行层（/dev/uinput 权限，待探针）的 R40 边界。
