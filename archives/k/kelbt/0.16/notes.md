# kelbt 0.16 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-21
- 编译器: clang++（OHOS 交叉编译，/data/service/hnp/bin/clang++）
- 状态: built（真机 shadow CI 通过）

## 软件说明
kelbt 是 Adrian Thurston 编写的 Backtracking LR 解析器生成器，读取
`.kl` / `.kh` 语法文件生成 C++ 回溯解析器，是 ragel/colm 家族的一员。
源码自带 AAPL 容器库（纯头文件，`aapl/`，LGPL-2.1）。

## 编译步骤
1. 下载源码 `http://www.colm.net/files/kelbt/kelbt-0.16.tar.gz`
2. 应用补丁 `patches/0001-configure-fix-hmdfs-tmpdir.patch`
3. `sh configure --prefix=/`（HMDFS 执行位受限，用 sh 显式执行）
4. `make -j1`
5. 产物：`src/kelbt`（单可执行文件，aapl 为 noinst_HEADERS 不安装）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 是否需要 ragel/kelbt bootstrap | 上游发布包 DIST 文件 `build_parsers=no`，已含生成的 klscan.cpp/klparse.{h,cpp} | 无需处理，直接 configure+make |
| 2 | config.guess 无法识别 OHOS | configure.ac 未调用 AC_CANONICAL_HOST，无平台检测 | 无需 --host/--build，依赖 AutotoolsToolchain 提供 CXX |
| 3 | R26 终端工具需静态链接 | 真机运行需避免依赖系统动态库 | OHOS 下 `tc.extra_ldflags.append("-static")` |
| 4 | 上游无 make check | automake foreign 且 Makefile.am 无 TESTS | 上游测试为空，test_package 自行构造消费验证 |
| 5 | `configure: Permission denied`（直接 exec） | HMDFS 屏蔽 other 执行位（E046/E047），文件 owner uid 与构建进程 uid 不一致，chmod 无效 | build() 用 `sh configure` 显式执行，绕过直接 exec |
| 6 | `configure: /tmp Read-only file system` | 鸿蒙 /tmp 只读（E002） | `os.environ["TMPDIR"] = "/data/storage/el2/base/cache"` |
| 7 | `config.status: subs1.awk Permission denied` | confXXX 临时目录在 HMDFS 的 $PWD，heredoc 创建的 awk 脚本权限异常（E087/E011） | 补丁 0001：ac_tmp 改用 `${TMPDIR:-/tmp}/confXXXXXX` + `chmod 700` |
| 8 | `klparse.cpp: error: -1 cannot be narrowed to char` | ARM64 上 char 默认 unsigned，`char arr[]={-1}` 触发 C++11 narrowing，而 kelbt 假设 char 为 signed | `tc.extra_cxxflags.append("-fsigned-char")` |
| 9 | package 后 bin/ 无 kelbt | 编译产物在 base_build/src，而 self.build_folder 是其下 build-release 子目录 | package() 用 `self.folders.base_build` 定位 src/kelbt |

## 源码修改
补丁 `patches/0001-configure-fix-hmdfs-tmpdir.patch`：仅修改 configure 的
ac_tmp 临时目录路径，使其落到可写的 TMPDIR 而非 HMDFS 的 $PWD。

## 依赖版本
无外部依赖（仅 C++ 编译器 + 内置 aapl 头文件）。

## 验证结果
- 本机前置验证（已完成）：
  - `git diff --check`、Python 语法、YAML/JSON 解析、bash -n、SHA256 复核均通过
- 真机 shadow CI（已完成，exit code 0）：
  - L0_RESULT=pass（quality gate + commands.json + 版本检查）
  - L1_RESULT=pass（test_package 执行，6/6 断言通过）
  - L2_RESULT=pass（`kelbt --version` 输出 0.16）
  - L4_RESULT=pass（补丁安全扫描）
  - L5_RESULT=pass（bin/ 有产物）
  - L1e 破坏性负向测试通过（test 真实依赖 kelbt）
  - `conan create` 成功，产物 `kelbt/0.16` 生成

## 下一步
- 提交 PR（单库单版本单分支，仅含 `archives/k/kelbt/`）
- CI 校验 + 合并后 release 流水线发布到制品仓
