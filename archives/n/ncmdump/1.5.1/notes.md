# ncmdump 1.5.1 适配笔记

## 编译环境
- 构建系统: cmake（CMake >= 3.14，C++17）
- 编译器: clang/clang++（OHOS 6.0 SDK，clang 15）
- 目标平台: OHOS 6.0 (aarch64, libc++, Release)
- 依赖: taglib/2.3（唯一硬依赖，已适配，ohpcd remote 有 OHOS 制品）

## 适配方案概述

ncmdump 是网易云音乐 NCM 加密文件解密 CLI 工具（taurusxin/ncmdump）。
非 Windows 分支只构建可执行文件 ncmdump，链接 TagLib::tag。

适配要点：
1. **TagLib 目标名映射**：上游 CMakeLists.txt 用 `find_package(TagLib REQUIRED)`
   并链接 `TagLib::tag`，而 taglib Conan 包暴露的目标是 `taglib::taglib`。
   在 recipe 的 generate() 中用 CMakeDeps 的 set_property 把 taglib 映射为
   cmake_file_name=TagLib、cmake_target_name=TagLib::tag，无需改动上游源码。
2. **无上游自动化测试**：上游无 CTest/enable_testing，test/ 仅含官方样例
   test.ncm（474KB）。test_package 用该样例做真实解密验证（-v + 解密 +
   魔数校验），不作为官方测试通过率的伪造依据。
3. **ELF 签名**：可执行文件需签名才能在鸿蒙执行，_sign_elf 在 CI 工作机上
   签名；本地无签名工具时跳过并告警。

## 编译步骤
```bash
export PATH="$HOME/.local/bin:$PATH"
PROFILE=ci/conan/profiles/ohos-aarch64
conan create archives/n/ncmdump/1.5.1 -pr:h=$PROFILE -pr:b=$PROFILE --build=missing
```

## 验证清单
- [x] conan create 成功
- [x] 编译无错误
- [x] test_package 真实解密 test.ncm 通过（L1）
