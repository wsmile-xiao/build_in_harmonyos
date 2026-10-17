# hsluv-c 1.0.0 适配笔记

## 概述
- 上游：https://github.com/hsluv/hsluv-c （官方 tag 1.0.0，commit 59539e04）
- 语言：纯 C99，单转换单元（src/hsluv.c + src/hsluv.h）
- 构建系统：CMake（无 install 规则，需配方手动打包静态库 + 头文件）
- 依赖：无（仅 libm）
- 版本策略：首次适配，上游版本号 1.0.0

## 下载与核验
- GitHub web 直连不可达（连接超时），api.github.com 可达
- 通过官方 codeload 通道下载 tag tarball，SHA-256 = bd37d8318aeacb4fd25481b70e0d5b628055b018b90a8e3ff88a741c8b629778
- 镜像通道（ghfast.top）下载同一 URL，字节一致（解压后逐文件 diff 为空），双通道交叉核验通过

## 适配要点
1. CMake 4.1.2 与上游 `cmake_minimum_required(VERSION 3.1)` 不兼容（CMake 4.x 移除 <3.5）
   → 配方 generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，不改上游文件
2. 上游无 install 规则 → 配方 package() 手动 copy hsluv.h 与 libhsluv-c.a（R26 静态交付）
3. OHOS 工具链 clang 15.0.4 (aarch64-linux-ohos) 下编译零告警通过

## 测试
- 上游 acutest：4 个独立 TEST_LIST 用例（hsluv2rgb/rgb2hsluv/hpluv2rgb/rgb2hpluv），各遍历 4096 条官方快照 → 全过
- 鸿蒙专项：test_package/test_hsluv_ohos.c（灰度轴/端点/往返闭包/网格恢复 100+32 个断言）
- 消费者验证：test_package/test_hsluv_consumer.c（rgb2hsluv/hsluv2rgb 与 #ff0000 官方参考值对照 + HPLuv 往返）

## 状态
built（本地 W3 验证通过后更新）
