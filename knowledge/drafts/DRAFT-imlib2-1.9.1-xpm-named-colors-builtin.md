# imlib2 1.9.1：XPM 命名色在无 rgb.txt 环境的内置表兜底

## 场景

imlib2 1.9.1 适配 HarmonyOS PC。上游测试 LOAD2.load_1 的 icon-64.xpm
加载成功但像素 crc 不匹配（预期 4016720483，实际 671661664）。直方图对比
gif 与 xpm：除背景色外完全一致——xpm 背景被解码成纯黑 ff000000，gif 为
白色 ffffffff。

## 根因

icon-64.xpm 颜色表含命名色：

```text
"aX c white",
```

loader_xpm.c 的 xpm_parse_color() 对非 `#` 前缀颜色仅查找
`/usr/share/X11/rgb.txt`（及 /usr/X11R6/lib/X11/rgb.txt、
/usr/openwin/lib/X11/rgb.txt）。OHOS 无 X11、三路径均不存在 → 解析失败
r=g=b=0 → 像素黑色 → 整图失真 → crc 不匹配。

## 修复

在 rgb.txt 查找失败分支内置常用 X11 颜色名表（`strcasecmp` 小写不敏感），
命中即赋值：white/black/red/green/blue/yellow/cyan/magenta/gray/grey/
orange/purple/brown/navy/teal/silver/maroon/lime/olive/aqua/fuchsia/gold/
pink/lightgray（24 项）。落地：`patches/0004-xpm-builtin-named-colors.patch`。

## 验证

- 修复前：icon-64.xpm 解码 p0=ff000000（黑），crc 671661664 ≠ 预期。
- 修复后：xpm 与 gif/png 解码一致（白背景），LOAD2.load_1 通过，
  上游测试 31/31。

## 边界

- 覆盖 24 个最常用 X11 颜色名；更生僻命名色仍需 rgb.txt 或 X11 环境。
- 反例：不解析命名色（只用 #hex）的 XPM 不受影响，无需此补丁。
- 可跨库复用：任何在无 X11 平台解析 XPM 命名色的图形库。

## 查重

| 既有条目 | 关系 |
|---|---|
| 无（XPM 命名色/rgb.txt 缺失无既有条目） | 全新组合 |
| DRAFT-boxfort-ohos-code-page-integrity / DRAFT-gcc-ada-ohos-xpm-seed-loader | 同词 XPM 但指内核代码页保护，无关 |
| E002（/tmp 只读） | 同类"环境缺失"但机制不同 |

同 stem 草稿：DRAFT-imlib2-1.9.1-xpm-named-colors-builtin.kv