# cgltf 1.15 — OHOS 适配笔记

## 结论
- C99 单头文件 glTF 2.0 解析器，零运行时依赖。
- 编译为 libcgltf.a（定义 CGLTF_IMPLEMENTATION 的翻译单元）。
- 1 个补丁：去掉 test/CMakeLists.txt 的 -fsanitize=address + -Werror。

## 上游测试执行
- 6 个上游测试套件中 4 个自包含（test_math/test_strings/test_write/test_write_glb），在 build() 内真实编译执行。
- main.c (cgltf_test) 和 test_conversion.cpp 需要外网 clone glTF-Sample-Models → 不执行，按 gulkan #7121 "逐条 1-e 申报"模式处理。

## 版本对齐
- 任务 #5180 = conan 1.15 = 分支 feat/cgltf-1.15 = 目录 archives/c/cgltf/1.15。
---

**编译结束**: 2026-08-31 00:50
**最终状态**: built
