# liboggz

## 简介
liboggz 1.1.1 — 一个用于读取、编写与操作 Ogg 媒体容器的 C 库（基于 libogg），由 Conrad Parker 开发，Xiph.Org 基金会发布。

## OHOS 适配
- 构建系统: autotools（configure + make）
- 目标平台: HarmonyOS PC aarch64（clang 15，profile ci/conan/profiles/ohos-aarch64）
- 依赖: libogg/1.3.5（ohpcd registry 已发布）
- 适配补丁: 4 个（config.guess/config.sub 2023 版、configure umask 修复、oggz_off_t 类型修复）
- 详见各版本 notes.md 获取适配详情

## 功能验证
- 上游测试 23/23 通过（make check）
- 消费者测试通过（test_package：oggz_new/oggz_close）
- W3 本地 CI 模拟通过
