# xva-img 1.5 HarmonyOS 移植设计

## 范围

- 适配上游 `https://github.com/eriklax/xva-img` 的官方 `1.5` tag。
- Conan 包归档放在 `archives/x/xva-img/1.5/`，软件级命令元数据放在 `archives/x/xva-img/commands.json`。
- 目标为 HarmonyOS 6.0、aarch64；在提供的真机上执行原生构建与运行测试。
- 不创建或提交 PR；本次完成本地分支上的适配和仓库要求的验证。

## 源码和依赖

- 官方源码归档：`https://github.com/eriklax/xva-img/archive/refs/tags/1.5.tar.gz`
- 已核验 SHA256：`89667EA86A5EC8CBF670966EEA9D758F4571A92004C798D8DF3E1AA0EAEA9235`
- 直接 Conan 依赖：`openssl/3.5.8.1`、`xxhash/0.8.4`；按仓库 W0 流程已确认两个配方在 `ohpcd` 可下载，版本 `xva-img/1.5` 尚未占用。
- 上游 CMakeLists 将头文件和库搜索路径固定为 `/usr/local`。保留 CMake 构建方式，移除这些固定路径，并通过 Conan CMakeDeps/CMakeToolchain 提供依赖；链接 Conan OpenSSL 配方导出的 `openssl::openssl` 与 xxhash 的 `xxhash::xxhash` 目标。
- 配方按命令行应用打包，安装 `xva-img`、许可证和必要元数据；遵照 R38 登记 CLI 命令。
- HarmonyOS PC 的 Conan 打包步骤会移除 SDK 占位 `.codesign` 并用 `binary-sign-tool` 签名已安装的 `xva-img`；消费者测试在临时副本上单独签名和运行。

## 上游测试审计

官方归档共 19 项。没有 `tests/` 或 `test/` 目录、CTest 注册、`check`/`test` 构建目标或内嵌测试驱动；MANIFEST 将按仓库规范记录 `upstream_tests_exist: false`、`upstream_test_total: 0` 和 `manual_audit` 依据。上游行为由真实运行打包后的程序验证。

## 消费者测试

`test_package` 将实际执行 Conan 生成的 `xva-img`：

1. 检查 `--version` 输出包含 `1.5.0`。
2. 用确定性磁盘夹具执行 `disk-import` 与 `disk-export`，比较输出和输入字节，覆盖 OpenSSL SHA1 校验和路径。
3. 构造有效 `.xxhash` 磁盘块，执行导出并核对字节，覆盖 1.5 新增的 XXH64 校验路径。
4. 篡改校验和，验证默认行为非零退出；加入 `--ignore-checksum` 后验证导出完成、输出正确且报告校验警告。

MANIFEST 将逐项说明文件、命令、断言数量与上游无测试审计，不虚报测试结果。

## HarmonyOS 专项与 CI 验收

- 在真机执行环境断言 `uname` 系统标识为 HarmonyOS，且目标 ELF machine 为 AArch64。
- 按仓库现有签名约定使用 `binary-sign-tool` 签名测试程序，再在真机上运行 CLI 和磁盘往返用例；这些原生运行断言作为 `harmonyos_specific_tests` 单独列入 MANIFEST。
- 使用仓库 `ci/conan/profiles/ohos-aarch64` 在真机运行 Conan `create`，覆盖包构建与 `test_package`。
- 在真机暂存本分支的完整工作树后运行 `ci/conan/build_and_test.sh` 定向 `archives/x/xva-img/1.5`，按 W3 官方 finish 流程记录 CI 日志和结果；`.ci-result.json` 由仓库流程生成，不手工伪造。
- 只有全部验收通过后，才在 `notes.md` 和报告中记录通过状态；失败则记录确切命令、日志与阻塞原因。

## 完成标准

- 归档目录符合 `SKILL.md` 与 tests 约定，配方、源码元数据、test_package、MANIFEST、软件级 `commands.json` 齐全。
- Conan aarch64 `create`、HarmonyOS 专项测试和仓库 W3 本地 CI 均真实执行并通过。
- 变更只包含 xva-img 软件目录及其版本归档，既有 `gcobol` 删除备份不纳入提交。

## 实施计划

### 1. 归档与 Conan 配方

- 新增官方 tag 的 `conandata.yml`，记录已核验的归档 URL、SHA256 和通用 CMake 适配补丁。
- 编写 Conan 2 application 配方，使用 CMakeDeps/CMakeToolchain、已预检依赖与仓库 OHOS profile；安装可执行文件、许可证和运行元数据。
- 补齐版本 `manifest.yaml` 与软件级 `commands.json`，只声明实际提供的命令。

### 2. 消费者测试和 MANIFEST

- 编写 `test_package/conanfile.py` 与驱动文件，确保 `test()` 通过 `self.run()` 真实执行被测程序。
- 加入版本输出、SHA1 导入/导出字节往返、独立生成的有效 XXH64 校验块，以及损坏校验和/忽略校验和用例。
- 完成 `test_package/MANIFEST.yml` 的上游审计与逐项测试说明；记录实际断言，不预填结果。
- OHOS profile 下复制并签名被测程序，增加 HarmonyOS 标识、AArch64 ELF 与真机执行断言。

### 3. 结构和依赖门禁

- 运行仓库规定的结构、格式和依赖预检；确认所用依赖版本与配方声明一致。
- 针对失败按首个真实根因修正；不改动仓库框架或其他软件包。

### 4. 真机 Conan 构建与本地 CI

- 将本分支当前完整源码快照暂存到真机专用临时目录，不覆盖真机已有目录。
- 使用 `ci/conan/profiles/ohos-aarch64` 执行 `conan create`，保存完整构建/测试日志。
- 在真机定向运行仓库 `ci/conan/build_and_test.sh` 的 W3 检查；确认 CMake 构建、消费者测试、ELF 与 smoke 检查均真实执行。
- 运行仓库官方 finish 流程生成 `.ci-result.json`；若工具或网络门禁阻塞，记录原始输出并报告，不手写通过结果。

### 5. 收尾

- 回填真实测试命令、断言数、设备/工具链信息和结果到 `notes.md`、MANIFEST 与报告。
- 核对相对 `upstream/main` 的最终差异仅涉及 `archives/x/xva-img/**`；确认无空壳测试、无未登记可执行命令、无虚报 CI 结果。
- 全部验收通过后在 `feat/xva-img-1.5` 留下最终实现提交；不推送、不创建 PR，除非之后另行要求。

## 真机验证结果（2026-10-01）

- 设备：HarmonyOS 6.0，`aarch64`；Conan 2.29.1、Clang 15.0.4、CMake 4.1.2。
- Conan 依赖预检通过；使用仓库 `ohos-aarch64` profile 执行 `conan create` 成功，真实运行 `test_package`。
- 仓库 W3 定向构建：1 个目标成功、0 个失败；L0、L1、L4、L5 通过。消费者测试 16 项断言通过，其中 HarmonyOS 专项 3 项。
- W3 L2 为非阻塞跳过：通用冒烟直接从 Conan 包目录启动应用时，运行环境未包含 `libxxhash.so.0`；消费者测试通过 `VirtualRunEnv` 提供 Conan 运行库路径后成功执行。当前 xxhash Conan 配方默认构建共享库。
- `.ci-result.json` 由仓库 `finish` 的 W3 步骤生成，`exit_code=0`；最终 W3 日志 SHA256 为 `39bf43765ff93b4cd43a7efbe96747f5ad783dbd4d7173f3f6ba49d78ab51b42`。原始日志和结果记录在本目录 `reports/` 与归档根目录。
- 完整 `finish` 命令的最终退出码为 1：独立 Conan Verify 阶段被工具临时注入的 `ghfast.top` 镜像连接超时阻断（日志见 `reports/conan-create.log`）；finish 其他知识完整性、快照原子性与 submit-readiness 检查也未全部通过。这不改变仓库 W3 的 `exit_code=0`，但因此不将完整 finish 标记为通过。
