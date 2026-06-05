# opus 1.4 编译笔记

## 编译日期
2026-05-19

## 构建系统
meson（autotools 因 config.guess 无法识别 HarmonyOS 而失败）

## 编译选项
```bash
meson setup build --prefix=$DEFAULT_PREFIX --buildtype=release
meson compile -C build
meson install -C build --destdir=$TEST_PREFIX
```

## 遇到的问题

### 1. autotools configure 失败
config.guess 版本 2018-02-24 无法识别 HarmonyOS，改用 meson。

### 2. meson.build have_arm_intrinsics_or_asm 变量未定义
根因：silk/meson.build 在 celt/meson.build 之前执行，但 silk 使用了 celt 中定义的变量。
解决：在主 meson.build 的第一个 subdir() 调用前添加变量定义。

### 3. HarmonyOS 动态库加载问题
动态链接的程序运行时报错 "Error loading shared library libopus.so.0"。
解决：使用静态库链接（已验证通过）。

## 功能验证
- opus_get_version_string: ✅ "libopus 1.4"
- 编码器创建: ✅ 48kHz mono VOIP
- 解码器创建: ✅ 48kHz mono
- 编码/解码: ✅ 成功

## 建议
推荐使用静态库链接（libopus.a），避免动态库加载问题。
