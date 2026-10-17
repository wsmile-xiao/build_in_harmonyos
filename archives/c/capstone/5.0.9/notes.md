# capstone 5.0.9 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang/clang++（OHOS SDK llvm）
- 状态: built（CI conan create + test 通过）

## 定位
- 产出动态 libcapstone.so，供 dlopen 及作依赖。
- 纯 C 反汇编框架，零外部依赖（requirements 为空）。

## 关键适配（复用 5.0.7 配方已验证方案）
- **OHOS 工具链自发现**（`_ohos_toolchain`）：① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
  ③ glob 设备/CI 的 SDK 布局，不依赖 CI profile host 段。
- **llvm-ranlib 缺失修复**（`_llvm_ranlib`）：OHOS SDK llvm/bin 下只有 llvm-ar 没有 llvm-ranlib，
  而 ohos.toolchain.cmake 仍把 CMAKE_RANLIB 指过去 → 造 .a 时 ENOENT；返回实际 llvm-ranlib 路径覆盖。
- **代码签名**（`_sign_binaries`）：鸿蒙 XPM 要求 dlopen 的 .so 代码签名，用 binary-sign-tool 自签
  （先 llvm-objcopy 移除旧 .codesign 段）。
- **关闭测试与工具**：CAPSTONE_BUILD_TESTS=OFF、CAPSTONE_BUILD_CSTOOL=OFF（无标准 make check 目标）。
- **install 路径**：-DCMAKE_INSTALL_LIBDIR=lib（ohos.toolchain 64 位默认装 lib64/）；configure 期给
  INSTALL_PREFIX（GNUInstallDirs 的 FULL_* 绝对路径在 configure 期算定，--prefix 覆盖不到）。

## 上游测试
- 上游无标准 make check 目标（CAPSTONE_BUILD_TESTS 关闭）。
- test_package 用**真实反汇编**验证（test.c）：已知 aarch64 机器码 `mov x0,#42; ret`，
  断言 cs_version>0、cs_support(ARM64)、cs_open 成功、反汇编助记符正确——"换个字节结果就变"的真计算。

## 与 5.0.7 的差异 / 本版本注意
- 5.0.9 为 5.0.7 之后的安全/bugfix 版本，CMake 构建选项不变，配方整体复用。
- **conandata.yml 已清除 gh-proxy.com 镜像残留**（5.0.7 配方曾残留，命中 CI PF7 源 URL 闸风险），
  仅保留官方 https 源；CI 会自动加镜像 fallback。
- 时间戳：`init-build` 误将构建系统识别为 autotools（实为 cmake），配方已显式走 cmake 路线。

## 历史
- 本仓库已有 5.0.6 / 5.0.7 / 5.0.7-r0 归档，本配方采用 cmake 路线（同 5.0.6/5.0.7）。

## 依赖版本
- 无（零外部依赖）。

## 验证结果
```bash
# 本地 finish / W3: conan create 编译 libcapstone.so 并签名
# test_package: 编译 test.c -> test_probe，运行后输出
#   capstone 5.0.9: 全部断言通过
```

## 注意事项
- 勿在 conandata.yml 引入 gh-proxy/cnb 等镜像域名（CI PF7 拦截）。
- os=OHOS 下须绕开 conan_toolchain（CMAKE_SYSTEM_NAME 映射异常），改用自发现 ohos.toolchain + 裸 cmake。
