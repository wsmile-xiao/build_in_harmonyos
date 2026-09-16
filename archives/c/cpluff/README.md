# cpluff

C-Pluff 是一个 C 语言插件框架, 深受 Eclipse Java 插件框架启发,
提供插件交互与插件管理的核心服务, 支持不停止整个应用即动态变更插件配置。

## 项目信息

- **官方仓库**: https://github.com/jlehtine/c-pluff
- **源码下载**: https://c-pluff.org/download
- **许可证**: MIT
- **语言**: C
- **构建系统**: autotools

## 版本历史

- **0.2.0**: 首次适配 OHOS 平台

## 适配说明

1. 显式 `--build/--host` triplet 绕过老旧 config.guess 对 HarmonyOS 的识别问题
2. `SHELL` 指向 bash 以满足 configure 与测试脚本的语法需求
3. expat 依赖经 `CPPFLAGS/LDFLAGS` 注入 (上游 AC_CHECK_LIB 探测不走 pkg-config)
4. 上游自定义 `make check` 套件 (53 用例) 在配方内完整执行
