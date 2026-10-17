# opengl 4.6 适配笔记

## 编译环境
- 构建系统: 无 (header-only 头文件包, 无编译)
- 编译日期: 2026-10-01
- 编译器: clang/clang++ (OHOS aarch64, profile ci/conan/profiles/ohos-aarch64)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build opengl 4.6 --url=https://github.com/KhronosGroup/OpenGL-Registry/archive/refs/heads/main.tar.gz --no-download`
2. 官方 tarball 经 ghfast 镜像下载 (github 直连不可达, 按 E017 use-ghfast), SHA-256 = 45dfcb6974ac5b89440a45322d9dcb013bc791ecfae9730e2afea41e61e94709
3. 解压至 tmp/builds/opengl-4.6.orig/.work (--strip-components=1, 1426 条目核验一致)
4. 编写 header-only 配方: conandata.yml (官方 URL + SHA-256), conanfile.py (package_type=header-library, package() 将 api/ 整树复制到 include/)
5. 补丁 patches/0001-add-khrplatform.h.patch: 引入官方 Khronos khrplatform.h (EGL-Registry api/KHR/khrplatform.h, 11131 字节, MIT)
6. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64` (含 test_package 消费者用例 + 鸿蒙专项测试)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时 (git ls-remote/api/raw 均连接失败) | 设备网络无法直连 GitHub | 按 E017 use-ghfast 规则, 经 https://ghfast.top/ 前缀下载官方归档; conandata.yml 仍保留官方 HTTPS URL (不写镜像) |
| 2 | OpenGL-Registry main 快照缺少 api/KHR/khrplatform.h, 但 glcorearb.h/glext.h/GLES 全部头文件都 `#include <KHR/khrplatform.h>` (原始 raw 404 证实) | 上游在 main 分支移除/迁移了该文件 | 补丁 0001 随包引入官方 Khronos khrplatform.h (从 EGL-Registry 仓库获取, 同一 Khronos 文件, MIT) |
| 3 | 首次 tar 解压到 tmp/builds 后, .orig/.work 树与 tarball 不一致 (find 计数 1080 vs 1426, api/ 缺失) | hmdfs 混合存储写后未同步/视图不一致 | 重新解压至新目录并逐条目核验 (1426/1426 一致) 后再使用 |

## 源码修改

- patches/0001-add-khrplatform.h.patch: 新增 api/KHR/khrplatform.h (官方 Khronos 文件, 11131 字节, sha256 7b1e01aaa7ad8f6fc34b5c7bdf79ebf5189bb09e2c4d2e79fc5d350623d11e83)

## 依赖版本

无编译依赖 (header-only)。

## 验证结果

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64` 退出码 0
- test_package 消费者用例 (test_package.c): ctest consumer 通过
- 鸿蒙专项测试 (harmonyos_test.c): ctest harmonyos 通过
- 包内容: include/GL, include/GLES, include/GLES2, include/GLES3, include/GLSC, include/GLSC2, include/KHR

## 注意事项

- 上游无版本 tag (v4.6 → 404), conandata 钉住 main 分支快照 URL + SHA-256, 以哈希保证可复现
- khrplatform.h 属上游缺口, 已用官方文件补齐, 相关候选进入知识台账 (路径 B)
---

**编译结束**: 2026-10-01 18:05
**最终状态**: built
