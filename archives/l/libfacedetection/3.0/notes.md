# libfacedetection 3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (clang 15.0.4, HarmonyOS PC 真机)
- 状态: built
- 目标平台: HarmonyOS PC (HongMeng Kernel 1.12.0, aarch64)

## 编译步骤

```bash
cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DENABLE_NEON=ON -DENABLE_AVX2=OFF -DDEMO=OFF -DUSE_OPENMP=OFF \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build -j2
cmake --install build            # 安装到 staging/usr/local
```

产物：libfacedetection.a + include/facedetection/{facedetectcnn.h,facedetection_export.h}
+ cmake/facedetection/facedetectionConfig.cmake（上游 export 自带）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake>=4 拒绝上游 `cmake_minimum_required(2.8.12)` | CMake 4 移除 <3.5 兼容 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（不改源码，本地与 CI 同源） |
| 2 | 上游直连 github.com 超时（DNS/TLS 基础设施） | 本机无法直连 GitHub | GitCode 镜像核验官方 tag v3.0 commit；codeload 慢速直下官方 tarball 核验 sha256=66dc6b47… |
| 3 | init-build 猜测构建系统为 autotools | URL 无扩展名导致误猜 | 以源码实际构建系统 CMake 为准，重写 CMake 配方 |
| 4 | lang-preflight 误判 mixed（gradle/maven） | 框架工具把辅助 mobile/Android demo 的嵌套 build.gradle 当作根 manifest（违反 R47「辅助脚本不算主体」） | 主体源码视图（排除 mobile/opencv_dnn/images 辅助 demo 目录）复验：cmake + cpp 100% 通过；共享框架零修改 |

## 源码修改

无（纯配方适配；补丁目录为空）。

## 依赖版本

无第三方依赖（模型静态内嵌于 facedetectcnn-data.cpp，见上游 README）。

## 验证结果

- 本地 CMake 构建：通过（clang 15, aarch64）
- test_package：构造 256x192 BGR 图像调用 facedetect_cnn 真实推理 API → PASS
- 上游测试清点（R51）：上游无 ctest/make check 注册；example/*.cpp 依赖 OpenCV（DEMO=ON），非库运行时依赖，未纳入配方构建

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（NEON/armv8、CMake>=4 兼容） |
| conandata.yml | 官方 v3.0 tarball + sha256 |
| test_package/ | 真实 API 消费者测试（facedetect_cnn） |
| manifest.yaml | 版本级元数据（upstream_identity 记录 tag→commit 核验） |

## 注意事项

- ENABLE_NEON 仅对 arm* 开启；x86 请改用 ENABLE_AVX2（本库面向鸿蒙 PC aarch64）。
- 上游 .gitignore 声明 export-ignore 的目录（mobile/opencv_dnn/images 为辅助 demo），不影响库构建。
---

**编译结束**: 2026-09-22 20:15
**最终状态**: published
