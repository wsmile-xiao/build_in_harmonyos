# album 4.18 — HarmonyOS PC (ohos-aarch64) 适配笔记

## 概述

album 4.18 是 marginalhacks.com 的**纯 Perl** HTML 相册生成器
（themeable HTML photo album generator），单脚本（`album`，约 2300 行）
+ 文档/许可证。无需 C/C++ 编译。配方以 `package_type=application` 打包
`bin/album`，运行时完全依赖目标环境的 Perl 解释器（`/data/service/hnp/bin/perl`）。

- 上游源码：https://marginalhacks.com/bin/album.tar.gz
- sha256：`923511437db2555cc36710924f57be3e9b36a62b46392fd8a56fa0f38b85243a`
- 许可证：BSD-style（`License.txt`，Marginal Hacks license）

## 依赖（运行时，非 Conan 构建依赖）

| 依赖 | 用途 | 说明 |
|------|------|------|
| Perl 解释器 | 运行 album 脚本 | 目标环境提供（`/data/service/hnp/bin/perl` 5.42）；`perl -c` 语法校验通过 |
| ImageMagick `convert`/`identify` | 生成缩略图/尺寸探测 | 目标环境运行时依赖；本 CI worker 未安装（见测试跳过项） |

album 无 Conan 构建依赖（W0 预检通过）。

## 适配要点

- **纯 Perl 无编译**：`build()` 仅做 `perl -c` 语法校验（`album syntax OK`）。
- **shebang**：OHOS 存在 `/usr/bin/env`（toybox，E037 已解决），脚本内 `#!/usr/bin/env perl`
  可直接工作；test_package 用 `sh` 调用避免 shebang 依赖。
- **chmod（E046）**：conan 包目录可写，`copy()` 安装的脚本保留执行位，无阻塞。
- **test_package 实质验证**：真实调用打包产物 `album --version` / `album --help`
  （必须通过），相册生成场景以 `command -v convert` 守卫。

## 测试统计

| 场景 | 结果 |
|------|------|
| `album --version` | PASS（输出 "This is album v4.18 on linux"） |
| `album --help` | PASS |
| 相册生成（缩略图） | SKIP（崩溃点/根因见下） |
| **合计** | **PASS=2 / SKIP=1 / FAIL=0** |

### 跳过项与崩溃点原因

| 场景 | 崩溃点/失败位置 | 根因 | 为何不可行 |
|------|----------------|------|-----------|
| 相册生成（ImageMagick 缩略图） | album 处理图片时 spawn `identify`/`convert` 子进程 → `File not found`（本环境 `command -v convert` 为空） | ImageMagick 是系统级运行时依赖，本 OHOS CI worker 未安装 | 系统级原生二进制超出纯 Perl 包适配范围；目标环境具备 ImageMagick 时该场景自动转 PASS（test.sh 已内置 convert 分支） |

## 上游测试

album 无正式上游测试套件（无 `make check`/`t/` 目录），故以 test_package
实质性功能验证为准（R34 满足：真实调用打包产物而非空壳断言）。

---

**适配日期**: 2026-08-09
**最终状态**: built
