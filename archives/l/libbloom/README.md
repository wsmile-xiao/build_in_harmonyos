# libbloom for HarmonyOS

## 概述

libbloom 是 Jyri J. Virkki 编写的极简 C 语言布隆过滤器实现，无第三方依赖，
适用于成员判定、缓存过滤等场景。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libbloom |
| 版本 | 2.0（上游 tag v2.0，2022-09-18） |
| 许可证 | BSD-2-Clause |
| 上游仓库 | https://github.com/jvirkki/libbloom |
| 依赖 | 无（仅系统 libm） |
| 构建系统 | Makefile（GNU Make） |

## 鸿蒙适配要点

- 上游 Makefile 用 `$(shell /bin/pwd)` 定位构建目录，在 OHOS 上 `/bin/pwd`
  可能不存在，打了最小 POSIX 补丁改用 `pwd`（无平台宏，PF5 安全）。
- 编译器/归档工具从 Conan conf 获取（R33），`make -j1`（R9）。
- 上游无 `install` 目标，`package()` 手动拷贝 `bloom.h` 与
  `build/libbloom.a` / `build/libbloom.so*`。
- 非系统同名库，动态/静态均保留（默认静态）。
- `build()` 末尾执行上游官方测试 `make test`（test-basic + test-libbloom），
  输出 `HMBS_UPSTREAM_TEST_RESULT` 证据标记。
- `test_package` 用 CMake 构建消费者测试，真实调用
  `bloom_init2/bloom_add/bloom_check/bloom_save/bloom_load/bloom_merge`，
  输出 `HMBS_TEST_PACKAGE_RESULT` 证据标记。

## 验证

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 参考

- https://github.com/jvirkki/libbloom
