# Sonnet 6.26.0 适配笔记

## 适配概况
- KDE Frameworks 6 拼写检查框架
- 构建系统：CMake
- 依赖：ECM 6.26.0, Qt6 6.11.1 (Core, Widgets, Test, LinguistTools)
- 后端：无后端（SONNET_NO_BACKENDS=ON），因 OHOS 上无 hunspell/aspell/voikko 等

## 适配要点
1. ECM 的 KDEPlatformCheck 需要 KF_IGNORE_PLATFORM_CHECK=TRUE 跳过平台检查
2. Qt6LinguistTools 需要从 qttools/6.11.1 包中获取
3. Qt6Widgets 需要从 qtbase-gui/6.11.1 包中获取
4. 禁用 QML 组件（SONNET_USE_QML=OFF，Qt6Quick 未发布到 ohpcd）
5. ECM_MODULE_PATH 需手动设置（CMakeDeps 生成的 ECMConfig.cmake 不传播该变量）
6. 需创建 conan_cmakedeps_paths.cmake 确保 CMake 能找到 Qt6 和 ECM 的 cmake 文件

## 测试结果
- 上游测试：5/7 通过 (71%)
- 通过的测试：test_core, test_suggest, test_autodetect, test_filter, test_settings
- 失败的测试：test_decorator, test_highlighter（需要 Qt6Widgets 运行时兼容性）
- 消费者测试：test_sonnet.cpp — 12 个断言全部通过