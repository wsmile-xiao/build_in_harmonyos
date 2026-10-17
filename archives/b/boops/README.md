# boops

BOops 是 sjaehn 开发的 LV2 glitch 效果序列器插件（https://github.com/sjaehn/BOops）。
本目录收录其在 HarmonyOS PC (aarch64) 上的适配配方。

## OHOS 适配
- **构建系统**: 纯 Makefile + pkg-config，`make BOops.so` 仅构建 DSP
- **依赖**: `lv2/1.18.11-git`、`libsndfile/1.2.2`
- **GUI 处理**: `BOopsGUI.so` 依赖 X11/cairo，在 OHOS 上禁用，仅验证 DSP
- **安装路径**: `lib/lv2/BOops.lv2/`（LV2 bundle 规范）

## 验证
```bash
pkg-config --modversion lv2
# 期望 LV2 bundle 存在
ls /path/to/package/lib/lv2/BOops.lv2/
```
