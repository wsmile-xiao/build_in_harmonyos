# tbox 1.8.0 — 鸿蒙 (HarmonyOS arm64) 编译归档

## 软件信息

- **名称**: tbox
- **版本**: 1.8.0
- **描述**: Glib-like multi-platform C library
- **许可证**: Apache-2.0
- **主页**: https://github.com/tboox/tbox
- **源码**: https://github.com/tboox/tbox/archive/refs/tags/v1.8.0.tar.gz
- **SHA256**: 3b919f61055b75fe9cb3796477468f6fe7524801d429e6ac48933ddde9caafbd

## 构建信息

- **构建系统**: xmake.sh（configure 脚本生成 Makefile）
- **平台**: harmonyos / arm64
- **编译器**: clang 15.0.4 (OHOS SDK LLVM)
- **编译状态**: published
- **编译日期**: 2026-06-30

## 产物

| 产物 | 说明 |
|------|------|
| libtbox.a | 静态库 (820K) |
| include/tbox/*.h | 公共 API 头文件 (406 个) |
| bin/demo | 测试程序 (450K) |

## 补丁

| 补丁文件 | 说明 |
|----------|------|
| patches/0001-src-tbox-platform-bsd-filelock.c.patch | 修复 TB_CONFIG_OS_HARMONYOS 宏检查，使 bsd/filelock.c 正确包含 sys/file.h |

## Conan 配方

- **引用**: tbox/1.8.0@ohpcd/stable
- **Profile**: ohos-aarch64
- **依赖**: 无
- **静态链接**: 是 (R26)

## 验证结果

- **conan-verify**: 8 道门禁全部通过 (G0-G4 + L2/L4/L5)
- **功能测试**: 48 个测试用例，44 通过，1 崩溃(内存调试器)，3 超时(同步原语)
- **Staging 验证**: 产物完整，.staging-verified 标记存在
