# robin_hood 3.11.5 适配笔记

## 基本信息
- 软件: robin_hood (robin-hood-hashing)
- 版本: 3.11.5
- 类型: header-only C++11 (单头文件 src/include/robin_hood.h)
- 上游: https://github.com/martinus/robin-hood-hashing
- tag: 3.11.5 (commit 9145f963d80d6a02f0f96a47758050a89184a3ed, 2022-01-14)
- 归档: https://github.com/martinus/robin-hood-hashing/archive/refs/tags/3.11.5.tar.gz
- SHA-256: 3693e44dda569e9a8b87ce8263f7477b23af448a3c3600c8ab9004fe79c20ad0

## 适配要点
- header-only 库，无需编译二进制；conanfile.py 仅打包 robin_hood.h 到 include/。
- 无第三方依赖（仅 C++ 标准库）。

## 上游测试
- 构建: cmake + clang++ (C++17)，目标 rh 测试二进制。
- 环境兼容：Clang 15 下需 `-Wno-deprecated-builtins -Wno-sign-conversion`（上游头文件
  `__has_trivial_copy` 弃用告警 + nanobench 第三方代码 sign-conversion 告警被 -Werror 拦截）；
  并禁用 clang-tidy（上游 .clang-tidy WarningsAsErrors=* 对短参数名报错）。
- 结果: 129 用例全部通过，2165108 断言 0 失败，74 跳过。

## Conan 验证
- profile: ci/conan/profiles/ohos-aarch64（default profile 的 libstdc++11 不被 OHOS clang 接受）。
- conan create: 通过，test_package 1/1 通过。
- 注意：本地 conan create 需要镜像源下载源码（github.com 直连超时），
  CI 的 build_and_test.sh 会自动对官方 URL 加镜像 fallback，conandata.yml 保留官方单值 URL。

## 已知限制
- 无。
---

**编译结束**: 2026-08-31 22:50
**最终状态**: built
