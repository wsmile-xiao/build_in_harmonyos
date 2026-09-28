# lightmapper 2.8 适配笔记

## 上游信息
- 仓库: https://github.com/ands/lightmapper
- 形态: 单头文件 C/C++ lightmap 烘焙库（lightmapper.h，public domain）
- 版本核验: 上游**无正式 release tag**（GitHub tags API 返回空列表），
  固定 master HEAD commit `4fd3bf4e2c07263f85d5d875ebdef061bc512dd4`
  （2022-01-03，即上游最后一次实质变更），sha256
  `6ff3983114871892720fe10f6b546d674d9c1cd084a5e6e7187456c79f754ad2`。
- 任务版本标识 2.8 由分析端给定：上游无标签可核对，以 release commit 为核验参照。

## 适配要点
- header-only：无编译、无链接、无安装，仅分发 lightmapper.h。
- 头文件公共 API 引用 GL 常量（GL_UNSIGNED_BYTE 等），实现区（
  LIGHTMAPPER_IMPLEMENTATION）引用桌面 GL 函数；GL 由消费者自带，包不依赖 GL。
- conanfile.py 走 header-only 模板：package_type=header-library，
  package_id 清空，include 目录分发。

## OHOS 专项
- 纯 CPU 图像后处理 API（lmImageMin/lmImageMax/lmImageClamp/lmImageDilate/
  lmImageFtoUB/lmImageSaveTGAub）可在无 GL 环境下编译链接并实际运行；
- test_package 通过 `gl_shim.h/.c` 提供 GL 常量与链接期 stub（运行时不会被
  调用），使头文件实现区能编译链接，测试实际执行 CPU 侧 API 并断言结果。

## 上游测试清点（R51）
- 上游 tarball 无 tests/ 目录、无 ctest/make check/meson test 注册；
  仅含仓库 Romer 示例 example/（交互式 GL 窗口程序，依赖 GLFW+GL）与
  example_images/。上游确无独立测试套件，故无上游测试可运行；测试覆盖由
  test_package 消费者测试承担（实际调用 CPU 侧 API 并断言）。
---

**编译结束**: 2026-09-27 19:33
**最终状态**: built
