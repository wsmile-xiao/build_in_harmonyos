# libcroco 0.6.13 适配 notes

## 环境背景

- 目标：HarmonyOS PC arm64（OHOS armv8 / clang-15，Conan profile `ci/conan/profiles/ohos-aarch64`）
- 依赖发布状态：glib/2.88.0.1 与 libxml2/2.15.3.1 已在 ohpcd 制品仓发布（W0 预检通过）

## 已知坑与决策

1. **官方源码获取**：`download.gnome.org` 为唯一权威（R39 只写官方 HTTPS URL，镜像由 CI 自动改写）。SHA-256 与官方 `.sha256sum` 一致，无 file:// 或缓存路径污染。
2. **config.sub 不认识 `aarch64-linux-ohos`**（2018-03-08 版本）：沿用 aalib 先例，`0001-config.sub-ohos.patch` 加入 `linux-ohos*` 候选；configure 显式传 `--host/--build=aarch64-linux-ohos`。
3. **依赖 .pc 注入**：configure.ac 用 `PKG_CHECK_MODULES` 检查 glib-2.0/libxml-2.0，生成阶段必须 `PkgConfigDeps.generate()` 注入 `PKG_CONFIG_PATH`（AbiWord 插件同类先例）。
4. **头文件目录**：安装到 `include/libcroco-0.6/libcroco`，`package_info.cpp_info.includedirs` 须指向 `include/libcroco-0.6`。

## 验证

- `conan create`（-pr:h/-pr:b=ohos-aarch64）实际构建通过
- 上游测试 test0–test6 + 4 个 shell 脚本按 testctl 逐项运行并与参考输出 diff
- 消费者用例 consumer.c 编译链接运行通过
---

**编译结束**: 2026-09-10 01:57
**最终状态**: built
