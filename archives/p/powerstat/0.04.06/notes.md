# powerstat 0.04.06 适配笔记

## 编译环境
- 构建系统: makefile（raw POSIX Makefile，单文件 C 项目，无 configure）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18 sysroot）
- 状态: built

## 编译步骤
1. `git worktree add` 创建专用 worktree `feat/powerstat-0.04.06`（从 main 1326b73f4e 创建）
2. 下载官方源码 tag `V0.04.06`（codeload.github.com，SHA-256 `91e9306525d9c84c7811c1f105426a2047fb94e27a2f98f2c88b334a6bff2a91`）
3. `make CC=clang -j1`：首错 E119（sockaddr_storage 重定义），应用宏守卫补丁后编译通过
4. `make install DESTDIR=...`：staging 安装验证通过
5. 编写 conanfile.py（raw-makefile CLI 配方）+ conandata.yml + test_package
6. `conan-verify`：G0-G4 + L2/L4/L5 全部通过（G2 干净构建含 test_package 消费者验证）
7. `finish published`：W2/W3 本地 CI 通过（.ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | redefinition of 'sockaddr_storage'（linux/socket.h vs sys/socket.h） | OHOS sysroot 两处定义冲突，源码含 linux/netlink.h→linux/socket.h | patches/0001-powerstat.c.patch 宏守卫 `_UAPI_LINUX_SOCKET_H` + `__kernel_sa_family_t`（查重：E119/E091 exact_duplicate） |
| 2 | conan create `tools.build:compiler_executables:c does not exist` | OHOS profile 该 conf 是字典，须整体 dict 读取 | `self.conf.get(..., check_type=dict).get("c")`（查重：E392 exact_duplicate） |
| 3 | conan create `No makefile found` | raw makefile 在 source_folder，make 默认在 build_folder | `self.run("make ...", cwd=self.source_folder)`（查重：E392 exact_duplicate） |

## 源码修改
- `patches/0001-powerstat.c.patch`：E119 宏守卫（+8/-0），头文件冲突修复

## 依赖版本
- 无第三方运行时依赖（仅链接 libm）

## 验证结果
- make 编译 rc=0；staging install rc=0
- conan-verify 8 道门禁全过（G2 干净构建 rc=0，test_package 消费者验证：`powerstat -h` + 版本断言均 rc=0）
- W3 本地 CI 模拟：`.ci-result.json` exit_code=0，log_sha256 `2f71e73832222f960180213ac1bb0510faf15e41b2149fef13faef15987302c2`
- 鸿蒙专项测试 `tests/ohos_netlink_probe.c`：编译 rc=0、运行 rc=0（NETLINK_CONNECTOR 沙箱 EACCES 平台观测，如实记录，日志 SHA-256 `1a44ab6e9b5bdaeb0157558b79e1104a054e4800a6c91fb76e5063bf547d7825`）
- 上游测试统计：source_declared_total=0（官方 tar 22 文件无任何测试目标，完整枚举见 reports/test-report.md）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | raw-makefile CLI 配方（package_type=application） |
| conandata.yml | 官方 tag URL + SHA-256 |
| test_package/ | 消费者验证（真实调用 CLI 二进制断言版本） |
| patches/0001-powerstat.c.patch | E119 宏守卫 |
| commands.json（软件级） | CLI 工具声明（R38/L0k） |
| tests/ohos_netlink_probe.c | 鸿蒙专项测试 |
| reports/ | conan-verify / test-report / w3-local-ci / knowledge ledgers |

## 注意事项
- NETLINK_CONNECTOR 在当前沙箱环境被 EACCES 拒绝：平台运行时限制，如实记录（E237/E303/E496 模式），不伪造通过
- W3 曾命中其他库既有基线标记文件（cloog/kics 的 .build-closed/.staging-verified）：已按基线隔离复验处理（隔离→复跑→原样恢复，pre==post SHA-256），未修改或提交该基线文件
- 知识路径判断：path_a_no_knowledge（全部候选被 E119/E091/E392/E237/E303/E496 完整覆盖，无新增差异，见 reports/knowledge-candidate-ledger.md）