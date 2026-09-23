# chrono 3.0.4 适配笔记

> 实际软件：Howard Hinnant/date 库 v3.0.4（header-only `date` + 编译型 `date-tz`），
> Conan 包名在本仓库登记为 `chrono`。

## 编译环境

- 构建系统：CMake
- 编译日期：2026-09-09
- 编译器：clang/clang++ 15.0.4（由 Conan OHOS profile 注入）
- 状态：built（conan create + conan-verify 通过）

## 配方策略

配方构建并安装 header-only 的 `date::date` 与静态优先的 `date::date-tz`。
时区库使用 `MANUAL_TZ_DB=ON`，由应用通过 `date::set_install()` 指定 tzdata 目录。

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 默认时区下载模式引入 curl | 上游在非 system/manual 模式下启用远程 tzdata API | 使用 manual tzdb，消除未强验证的隐式依赖 |
| system tzdb 可能假设 `/usr/share/zoneinfo` | OHOS 设备不保证 Linux 的目录布局和软链接行为 | 不启用 `USE_SYSTEM_TZ_DB`，由消费者显式提供 tzdata |
| 包名与上游 CMake 包名不同 | 归档名为 `chrono`，上游导出 `date` | `package_info()` 映射为 `date::date` 和 `date::date-tz` |
| compile-fail helper 硬编码 `/bin/bash` | Harmony PC 的 bash 位于 `PATH`，不存在 `/bin/bash` | 将主脚本及生成 helper 的 shebang 改为 `/usr/bin/env bash` |
| `current_zone()` 忽略 POSIX `TZ` | Harmony PC 不提供上游探测的 `/etc/localtime` 等系统时区文件 | 仅在 `TZ` 可定位为 IANA zone 时采用；规则串、冒号路径和无效值安全回退到原平台探测链 |
| codeload URL 无扩展名导致 Conan 无法解包 | `get()` 从 URL basename 推断格式，`v3.0.4` 无 `.tar.gz` 后缀 | conandata.yml 使用官方 GitHub archive URL（含 `.tar.gz`），E017 自动镜像 ghfast.top |
| /tmp 分区写满导致下载截断 | 本地 /tmp 100% 占用 | 使用 TMPDIR=/storage/Users/currentUser/tmp（init-build 默认） |

## 源码修改

`refresh-patch --auto` 已按 **per-file** 重命名补丁（文件名与 `patches/` 目录、
`conandata.yml` 三方一一对应，共 3 个）：
- `0001-compile_fail.sh.patch` — 让官方 compile-fail 测试脚本从 `PATH` 解析 bash；
- `0002-src-tz.cpp.patch` — 让非 Windows `current_zone()` 尝试采用可定位的 IANA `TZ`，
  并对 POSIX 规则串、冒号路径和无效值保留原平台探测链；
- `0003-test-tz_test-zoned_time_deduction.pass.cpp.patch` — 为既有
  `zoned_time_deduction` CTest 增加 IANA 与 fallback 回归断言。

未删减、跳过或豁免任何上游测试 case。

## 依赖版本

无 Conan 三方依赖。`date-tz` 在 OHOS 上链接系统 pthread。

## 验证结果

- W3 本地构建（手动 CMake，flags 与配方一致）：108/108 通过、0 失败（TZ=UTC，tzdata2026b）
- conan create（conan-verify G2，干净构建）：`100% tests passed, 0 tests failed out of 108`
- test_package 消费测试：`chrono checks passed: 220`
- conan-verify 门禁：G0-G4 + L2/L4/L5 全部 PASS

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，静态 date-tz，MANUAL_TZ_DB |
| conandata.yml | 官方源码 + tzdata2026b + 3 个补丁（patch_file 与 patches/ 文件名一致） |
| patches/0001-compile_fail.sh.patch | bash shebang 可移植修复 |
| patches/0002-src-tz.cpp.patch | TZ 环境变量采纳 + fallback |
| patches/0003-test-tz_test-zoned_time_deduction.pass.cpp.patch | current_zone TZ 回归断言 |

## 注意事项

- 消费者若使用时区查询 API，必须先准备 tzdata 并调用 `date::set_install()`。
- 包本身不启用运行时远程下载模式；固定 tzdata 只在官方上游测试构建阶段下载并校验。
- 不创建 `commands.json`：产物是库和头文件，不是命令行工具。

## 发现与知识

- ✅ Manual tzdb 模式避免隐式 libcurl 依赖和 Linux zoneinfo 布局假设（ref: E276, howard-hinnant-date/3.0.4）
- ✅ Conan 包名 chrono 与上游 CMake 包名 date 不同，package_info 需映射 date::date / date::date-tz（ref: howard-hinnant-date/3.0.4）
- ✅ TZ 环境变量候选需在 POSIX 规则串/冒号路径/无效 IANA 名时回退原平台发现链（ref: E315, howard-hinnant-date/3.0.4）
- ✅ finish 内置 refresh-patch --auto 会按 per-file 重命名补丁，conandata.yml patch_file 需同步新名，否则 export_sources() 报 Patch file does not exist（ref: E560, howard-hinnant-date/3.0.4）

---

**编译结束**: 2026-09-09 13:55
**最终状态**: built
