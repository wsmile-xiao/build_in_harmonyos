# W0 依赖发布检查报告 — libsbsms 2.3.0

> 任务: `libsbsms/2.3.0`（`feat/libsbsms-2.3.0`）
> 日期: 2026-09-15
> 依据: SKILL.md §0.3 W0；R35（禁止用 `conan list` 判 binary）；R36（依赖先发布）

## 一、结论

**通过 — 本包无任何依赖，不需要等待任何前置包发布。**

## 二、依赖来源清点

判定不是"配方里没写 requires"这种自证，而是从源码构建图直接清点：

| 清点对象 | 命令 | 结果 |
|---|---|---|
| CMake 目标源文件 | `CMakeLists.txt` 的 `add_library(sbsms ...)` | 11 个 `src/*.cpp`，全部属于本包 |
| CMake 依赖查找 | `grep -nE 'find_package\|target_link_libraries\|pkg_check' CMakeLists.txt` | 无命中 |
| autotools 库源 | `src/Makefile.am` 的 `libsbsms_la_SOURCES` | 仅本包源文件 |
| autotools 链接项 | `src/Makefile.am` 的 `libsbsms_la_LDFLAGS` | 仅 `-no-undefined` |
| 头文件包含 | `grep -rn '#include <' src include` | 仅 C/C++ 标准库（`math.h`/`string.h`/`stdlib.h`/`xmmintrin.h` 等） |

Debian 的 `libsndfile1-dev` 构建依赖**不适用**：它只服务于 Debian 自己打包的
示例/测试程序，而上游 2.3.0 仓库并不包含这些程序（见
`upstream-test-inventory.md`）。本包交付的是纯库，不含 `bin/`。

## 三、工具预检输出

```console
$ bash ci/scripts/preflight_check.sh libsbsms/2.3.0 --deps ""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  适配前预检: libsbsms/2.3.0
  制品仓: ohpcd
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO] 未找到依赖声明（conanfile.py 尚未生成或无依赖）。
[INFO] 如果是首次适配，这是正常的。适配生成 conanfile.py 后可再次运行检查。
[OK] 预检通过（无依赖需要检查）
rc=0
```

conanfile.py 生成后复跑结论不变（`requirements()` 未声明任何 `requires`）。

## 四、包名与版本权威性核对

任务卡软件名 `libsbsms` 与版本 `2.3.0` 经独立核对：

- `git ls-tree -r --name-only upstream/main | grep -i sbsms` → 零命中（确认是**全新包**，
  不是平台别名）；
- 上游 GitHub `claytonotey/libsbsms` 的 tag 列表为 `2.3.0` / `2.2.0` / `2.1.0`，
  `2.3.0` 为最新（GitHub API `/repos/claytonotey/libsbsms/tags`）；
- Debian trixie 的源码包亦为 `libsbsms 2.3.0-1`，`Upstream-Contact: Clayton Otey`，
  `Source: https://github.com/claytonotey/libsbsms`。

因此 `archives/l/libsbsms/2.3.0/` 的目录名与 CI 分支名门禁
（`feat/libsbsms-2.3.0` → 包目录名-版本）一致。
