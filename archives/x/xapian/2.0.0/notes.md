# xapian 2.0.0 移植记录

状态: built（HarmonyOS 6.0 真机 Conan / W3 验证通过；未发布）

## 包与源码

- Conan 包身份：`xapian/2.0.0`。
- 上游项目及源码包名：Xapian Core，`xapian-core-2.0.0.tar.xz`。
- 官方源码：`https://oligarchy.co.uk/xapian/2.0.0/xapian-core-2.0.0.tar.xz`。
- SHA256：`6cea3f49952a47224439a40bdb3608f928d121ad8721b9921cc42802d548ecf8`，与归档 `xapian-core/2.0.0` 的来源校验值一致。
- 构建系统：Autotools；目标：HarmonyOS PC aarch64，OHOS SDK clang/clang++。
- 唯一第三方硬依赖：`zlib/1.3.1.1`。该 built 版本是 zlib 1.3.1 的修复版本；不依赖尚在移植的 zlib 1.3.2。

## 参考归档与适配

`archives/x/xapian-core/2.0.0` 已有相同上游源码、相同目标平台的已归档移植。本包复用其五个已验证补丁，不修改原归档：

1. `0001-backends-uuids.cc.patch`：当 HarmonyOS 用户无法读取 `/proc/sys/kernel/random/uuid` 时，使用 `/dev/urandom` 生成 UUID。
2. `0002-config.guess.patch`、`0003-config.sub.patch`：识别 HarmonyOS 和 `linux-ohos` triplet。
3. `0004-configure.patch`：使用 toybox sed 可处理的 POSIX 地址表达式，并避免 HMDFS 上 `umask 077` 导致 configure 临时目录不可用。
4. `0005-tests-api_backend.cc.patch`：权限测试按当前文件系统实际产生的模式比较，适配 HMDFS 权限掩码。

Conan 名称改为 `xapian`；CMake 消费目标为 `xapian::xapian`。上游 pkg-config 模块仍叫 `xapian-core`，故配方保留该模块名。上游仍随库安装命令行工具，因此软件级 `commands.json` 声明 `xapian-check`、`xapian-delve` 和 `xapian-compact`。

## 测试设计

`test_package` 从消费者角度验证版本宏、in-memory 检索、glass 数据库读写、glass 到 honey 的压缩及 honey 查询；随后在 Conan `conanrun` 运行环境中执行 `xapian-check xapian_test_db_glass`，检查生成的 glass 数据库表结构。HarmonyOS 编译时还执行专属 UUID 测试：探测 procfs UUID 端点；若受限则检查 `/dev/urandom` 可读，并通过创建 glass 数据库执行 Xapian 的 UUID fallback 路径。

上游 `make check` 在参考归档中有完整运行记录：3617 个 case-runs 中 3545 通过、70 跳过、1 个预期失败，另有 1 个 `qp_scale1` CPU 计时门限波动失败。参考记录未修改该上游测试。它属于 `xapian-core/2.0.0` 的历史验证，不替代本包的 Conan 和本地 CI 结果。

## 本次验证记录

| 检查 | 结果 |
|------|------|
| 配方语法 / Conan inspect | 通过；本地 Python 配方语法检查通过，`conan inspect` 返回 `xapian/2.0.0` |
| 新包 `xapian/2.0.0` Conan create | HarmonyOS 6.0 真机干净源码构建通过；依赖使用制品仓 `zlib/1.3.1.1` built 二进制 |
| 新包 test_package | 12/12 断言通过：版本宏、in-memory/glass/honey 后端和检索；HarmonyOS 两项 UUID 专属断言通过；`xapian-check` 检查 glass 数据库并报告 `No errors found` |
| Conan verifier | G1–G4 通过 |
| 本地 CI W3 | 通过；W3 摘要为 1/1 包成功、100%；详见 `reports/w3-local-ci.log` 和 `.ci-result.json` |
| HarmonyOS 6.0 真机测试 | 通过；当 procfs UUID 端点受限时，`/dev/urandom` 可读且 Xapian glass 数据库创建成功 |
| clean-verify 辅助步骤 | 隔离副本中缺少原始 tarball，因此该辅助步骤未运行；Conan verifier G2 已独立从官方源干净构建通过 |

W3 中有三项非阻塞扫描/探测告警需要按实际证据解读：L2 的裸环境 `--version/--help` 探测没有加载 Conan 运行时路径；本包的 `conanrun` 消费者检查已成功运行 `xapian-check`。L4 的宽泛危险函数扫描将 `config.guess` 注释中的普通单词 `targets` 命中为告警，五个补丁中没有对应的危险函数调用。L1c 将 `xapian-check` 字符串误认作 `make check`；配方没有运行上游 `make check`，`test_package/MANIFEST.yml` 中也明确设为 `upstream_test_in_build: false`。

完整 `finish` 的 W3 后步骤没有全部通过：通用归档校验提示缺少 `packaging/`、release/debug tarballs；W5 报出仓库既有的 E219、E253、E305 字段缺失；提交就绪检查还要求打包目录和 `.staging-verified`。该检查同时要求 `test-report.md`，现已补入本归档；打包目录和 staging 标记仍未创建。这些不影响本次 W3 与 Conan 测试结果，也未生成占位发布产物或提交 PR。

## 发现与知识

- ✅ HarmonyOS 6.0 设备上，Conan HMDFS 构建目录可由 `/system/bin/sh` 正常 `getcwd`，HNP bash 则可能报 `getcwd` 失败；OHOS Autotools 配置显式固定 `CONFIG_SHELL=/system/bin/sh`。
- ✅ `apply_conandata_patches` 修改 Conan 的构建源码副本；从未打补丁的 `source_folder/configure` 启动会漏掉同目录的 `config.guess` 适配，因此配方从 patched build copy 运行 configure。

## 对话记录

### 对话 #1 — 归档身份与设备验证（2026-09-27）

- 用户要求在独立 `archives/x/xapian/2.0.0` 建包，并参考已归档的 `xapian-core/2.0.0`。
- 依赖按用户指定使用 built 状态的 `zlib/1.3.1.1`；制品仓实测可下载 recipe 和 OHOS aarch64 二进制。
- 新包通过 HarmonyOS 6.0 真机 Conan 源码构建、消费者测试、Conan verifier 及仓库 W3 本地 CI。
- 消费者测试另用 `xapian-check` 校验 glass 数据库；经 `conanrun` 执行结果为 `No errors found`。
- W3 首轮被隔离测试副本中误跟踪的 `.pyc` 文件拦截；移除临时字节码后再次运行通过。
- 更新 CLI 检查后重新运行 Conan test_package 与 `finish` W3，12 项断言及数据库完整性检查通过；W3 回执哈希对应最新日志。完整 `finish` 的后续归档/图谱/提交就绪步骤仍报告上述缺项。
---

**编译结束**: 2026-09-27 10:36
**最终状态**: built
