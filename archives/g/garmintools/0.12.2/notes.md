# garmintools 0.12.2 适配笔记

## 编译环境
- 构建系统: meson（上游 meson.build，非 autotools）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 1. meson 配置（libusb-1.0 依赖通过 Conan PkgConfigDeps 注入）
meson setup build --native-file <conan_meson_native.ini> \
  --buildtype=release --prefix=/ -Dpython-module=false -Ddefault_library=static
# 2. 编译
meson compile -C build
# 3. 安装（DESTDIR 隔离）
DESTDIR=<package> meson install -C build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan source() BadZipFile | api.github.com tarball URL 无扩展名，conan get() 误判为 zip | 改用 codeload.github.com URL 并显式声明 filename: garmintools-0.12.2.tar.gz |
| 2 | meson 找不到 libusb-1.0 | 手动 meson setup 未加载 MesonToolchain 生成的 native 文件 | build() 传入 --native-file <generators>/conan_meson_native.ini（含 pkg_config_path） |
| 3 | test_package 头文件 not found | package_type=application 时 cpp_info 默认 includedirs 为空 | 显式 self.cpp_info.includedirs = ["include"] |
| 4 | test 二进制运行时 dlopen libgarmintools.so.6 报 Permission denied | conan 缓存安装产物 RUNPATH 字符串被 X 掩码（scrub），musl 加载器拒载 | 配方 -Ddefault_library=static 静态链接消费者测试，规避运行时动态库加载 |
| 5 | CLI 工具未安装 | 上游 meson.build 的 executable() 无 install: true | 补丁 src/meson.build 为 7 个 CLI 工具加 install: true（packages/ 未用，直接体现在配方构建中） |

## 依赖版本

- libusb/1.0.27（ohpcd 已发布）

## 验证结果

```bash
# conan create（G2）+ 系统同名库隔离（G3）+ 产物完整性（G4）全部 PASS
# test_package 消费者测试 5 项断言全部 PASS：
#   garmin_lpid/garmin_gpid 协议映射 + garmin_load 错误路径
#   注：Pid_Wpt_Data 与航路点在 L001 链路层共用 L001_Pid_Rte_Wpt_Data，
#       逆向 garmin_gpid 解析回 Pid_Rte_Wpt_Data（上游映射非对称）
```

## 上游测试

上游 garmintools 0.12.2 无任何测试：meson 未注册 test() 目标，源码树无 tests/ 目录、
无 ctest/meson 测试清单、无独立测试源文件（仅 doc/man 手册与 extras/ 辅助脚本）。
因此源码声明测试总数 = 0；新增鸿蒙专项消费者测试 1 个（test_package，见上）。
---

**编译结束**: 2026-09-21 01:20
**最终状态**: built
