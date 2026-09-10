# apriltag 3.4.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-08
- 编译器: clang (aarch64-linux-ohos, clang 15.0.4)
- 状态: built

## 编译步骤

apriltag（AprilTag 3，AprilRobotics）为视觉基准 tag 检测库：灰度图上跑四线检测/
编解码/位姿估计，纯 C99 + CMake，仅依赖系统 threads + libm（W0 依赖预检通过）。

1. 官方源码：https://github.com/AprilRobotics/apriltag/archive/refs/tags/v3.4.5.tar.gz
   - sha256=3749f48220db78c29c375a373861f4e1f4138e5dbae3c298584e96cfcc556515
   - 哈希由「git -c core.autocrlf=false archive v3.4.5」在 LF 下重算，并与
     Debian/Ubuntu pool 同源 apriltag_3.4.5.orig.tar.gz（sha 一致 3749f48…）
     交叉验证：内容逐字节一致（Windows git 默认 autocrlf 会把整包污染成 CRLF）。
2. Conan 配方：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同`。
   - CMakeToolchain generic_system 块：OHOS → cmake_system_name=OHOS、
     cmake_system_processor=aarch64（与本仓 gcem/platform_folders 一致）。
   - `BUILD_SHARED_LIBS=OFF` 默认静态；`BUILD_EXAMPLES=OFF`、`BUILD_PYTHON_WRAPPER=OFF`。
   - `BUILD_TESTING=ON`：test/CMakeLists.txt 注册 3 个 ctest（test_detection 对
     3 张随包照片跑 tag36h11 全流程，与 test/data/*.txt 真值逐角点比对容差 0.1px），
     build() 内 `cmake.test()` 直接实跑 3/3。
   - 补丁 0001-drop-werror：上游把 -Werror 当静态库卫生——CMake>=3.24 走
     `set(CMAKE_COMPILE_WARNING_AS_ERROR ON)`（**无 CACHE**，-D 覆盖不掉）、
     <3.24 走 `add_compile_options(-Werror)`。clang-15 告警不致命，补丁摘除。
   - 上游 install 保目录把头装到 `include/apriltag/`（apriltag.h + common/*.h +
     tag*.h）；package_info 设 `includedirs=["include/apriltag"]`，
     `libs=["apriltag"]`，system_libs m+pthread，导出 apriltag::apriltag / apriltag.pc。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机（CN Windows）GitHub 直连不可达 | 网络限制 | gitcode gh_mirrors 镜像浅克隆 v3.4.5 tag 读源码；哈希用 Debian pool orig + LF git archive 交叉定 |
| 2 | `git archive` 算出的 sha256 与上游 GitHub 不一致 | Windows git core.autocrlf 把整包 CRLF 化 | `git -c core.autocrlf=false archive` 产出 LF 树；与 Debian orig 全文件 diff=0 |
| 3 | 上游 -Werror 摘不掉 | `set(CMAKE_COMPILE_WARNING_AS_ERROR ON)` 无 CACHE，`-DCMAKE_COMPILE_WARNING_AS_ERROR=OFF` 无效 | 补丁 0001 直接删该 if/else 块 |
| 4 | CMake 未知平台行为 | OHOS 非 CMake 原生平台 | generic_system 显式 cmake_system_name=OHOS/processor=aarch64 |

## 上游测试说明

- 上游自测入口：`-DBUILD_TESTING=ON` 后 `ctest` 跑 3 个 `test_detection_*` 用例。
- 每个用例编译同一个 `test_detection`（test_detection.c + test/getline.c），对一张
  真实 Flickr 照片跑 tag36h11 检测，把检测结果与 `test/data/*.txt` 真值逐角点
  比对（排序稳定，容差 0.1px）。照片/真值均随源码包分发 → 无需网络即可实跑。
- conan build 内 `cmake.test()` 实跑 3/3（L1）；test_package 另以消费者视角
  matd 数值断言 + tag36h11 family 字段 + 全白图 detect=0 验证（R34 反空壳）。
