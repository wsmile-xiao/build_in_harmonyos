# cpp-channel 1.3.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only，INTERFACE 库 msd_channel）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（OHOS 交叉工具链）
- 状态: built

## 编译步骤

cpp-channel 是纯 header-only 的 C++11 库（`include/msd/*.hpp`，共 5 个头文件），
上游 CMake 工程构建 `msd_channel` INTERFACE 库（无编译产物），仅需将头文件与
LICENSE 安装到 include/ 与 licenses/。因此 Conan 配方采用 header-only 变体：
无 `build()` 步骤（不伪造编译日志，R34），`package()` 只拷贝头文件，
`package_id()` 清空（单 package_id，无 os/compiler 依赖）。

```bash
# 生成配方骨架
python3 scripts/ohc-run.py conan-init cpp-channel 1.3.1
# 按 header-only 特性重写 conanfile.py（误判 autotools → headeronly 模板）
# 修正 conandata.yml sha256 为实际归档校验和
# test_package 改为真实调用 msd::channel API 的 test.cpp（R34）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 按 autotools 生成配方 | 构建系统探测优先命中 Makefile（上游仓库含 Makefile），但实际为 header-only CMake 库 | 按 v12.21 header-only 模板重写 conanfile.py，删除 Autotools 构建逻辑 |
| 2 | 初始 test.c 为空壳测试（仅 printf） | conan-init 模板默认生成 | 重写为 test.cpp，实际调用 channel::write/read/close/drained 与 static_channel，R34 合规 |
| 3 | /tmp 只读导致下载失败 | 平台限制（E002） | 下载目录改用 $HOME/tmp |

## 源码修改

无补丁。header-only 库在 OHOS 平台无需平台宏或源码修改；upstream 源码按 tag
v1.3.1（ef127e6be9bd64b9003ff2daf3d2729ddb8891fa）原样使用。

## 依赖版本

无第三方依赖（header-only，仅标准库 + pthread）。

## 验证结果

```bash
# conan create 验证（G2，含 test_package 消费者测试）
python3 scripts/ohc-run.py conan-verify cpp-channel 1.3.1
# 上游测试（googletest，3 个测试程序）
# 见 reports/ 与 test_package/MANIFEST.yml 申报
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=library，no_copy_source） |
| conandata.yml | 官方 tag 归档 URL + SHA-256 |
| test_package/ | 消费者验证：test.cpp 真实调用 channel API |
| test_package/MANIFEST.yml | 上游测试三步法申报（R51） |

## 注意事项

- header-only 库无编译产物，commands.json 不需要（R38：库类型不需要）。
- 上游测试依赖 googletest（FetchContent 拉取 release-1.12.1），非本库必选依赖，
  不作为 requires 声明；上游测试验证单独以真实运行结果申报（R51）。
---

**编译结束**: 2026-09-22 20:53
**最终状态**: built
