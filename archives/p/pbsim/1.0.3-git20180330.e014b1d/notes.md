# PBSIM 1.0.3-git20180330.e014b1d 适配笔记

## 编译环境
- 构建系统: 上游为 autotools（`configure.ac` + `Makefile.am` + `src/Makefile.am`，无预生成 `configure`）；本配方**直接用 clang++ 编译 3 个 .cpp**（见下）
- 编译日期: 2026-10-03
- 编译器: OHOS SDK clang++（Conan profile 的 `tools.build:compiler_executables.cpp`）
- 状态: built

## 编译步骤

1. 取 Debian dfsg orig 源码包 `pbsim_1.0.3+git20180330.e014b1d+dfsg.orig.tar.xz`。
2. `build()` 直接用
   `clang++ -O2 -Isrc -o src/pbsim src/pbsim.cpp src/helpers.cpp src/output.cpp -lm`
   编译（不定义 `HAVE_CONFIG_H`），产出 `src/pbsim`。
3. `package()` 安装 `bin/pbsim`、`licenses/{COPYING,README*}`。
4. `test_package/test_pbsim.sh` 运行 7 项检查。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf -i && ./configure` 失败（详见上）：`config.status: .../subs1.awk: Permission denied` → `could not setup config files machinery` | OHOS HMDFS 沙箱下 config.status 生成的临时 awk 辅助脚本无法执行；`config.guess` 也不认 HarmonyOS（`cannot guess build type`） | 放弃 autotools：pbsim.cpp 仅在 `HAVE_CONFIG_H` 时包含 `../config.h`，不定义该宏即可直接用 clang++ 编译 3 个源文件 |
| 2 | C++ 工具链 | 源码为 `.cpp` | 用 profile 的 `tools.build:compiler_executables.cpp`（ohos clang++） |

## 源码修改

无。零补丁。

## 依赖版本

无三方依赖（仅 libc/libc++ 与 `-lm`）。

## 验证结果

```bash
# 消费者（test_package/test_pbsim.sh，7 项）
PBSIM_CHECK_SUMMARY checks=7 fails=0
```

## 注意事项

- 上游无测试套件，按 §3.6 口径声明上游 N=0，另加鸿蒙特有（消费者）测试 7 项。
- 版本串为 Debian 上游快照 `1.0.3-git20180330.e014b1d`（对应上游 commit `e014b1d`）。
