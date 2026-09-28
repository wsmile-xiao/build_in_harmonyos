# fcitx5-utils

## 简介
Fcitx5Utils — fcitx5 输入法框架底层工具库（fcitx5 源码树 `src/lib/fcitx-utils` 组件），
提供 stringutils / Key / Semver / StandardPaths / EventLoop 等基础能力，
是 libime / fcitx5 / libime-jyutping 生态的公共依赖组件。

## OHOS 适配
- 构建系统: cmake
- 上游无独立发布仓库，源码取自 fcitx5 官方 tag 5.1.13
- 独立构建用配方内 wrapper CMakeLists 等价复刻顶层上下文（ECM / find 模块 / config.h）
- OHOS 需真实 libintl（gettext 包），sysroot 的 libintl.h 为空壳
- 详见各版本 notes.md 获取适配详情

## 依赖
- gettext/0.22.5.1（libintl）
- extra-cmake-modules/6.19.0（ECM，构建期 tool_requires）
- DL/Pthread（OHOS sysroot 自带）

## 功能验证
- test_package：find_package(Fcitx5Utils 5.1.13 REQUIRED) + 真机运行 stringutils/Key/Semver/StandardPaths API
- 详见各版本 test_package/MANIFEST.yml

## 参考
- https://github.com/fcitx/fcitx5