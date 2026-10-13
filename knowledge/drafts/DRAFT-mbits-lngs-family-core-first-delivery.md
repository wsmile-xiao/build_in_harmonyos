# 子模块测试框架与家族依赖同时缺失时按精确 pin 自建并恢复全量测试

## 错误特征

上游把测试框架放在 Git 子模块中，CLI 与部分测试依赖同族 Conan 包。官方标签归档缺少子模块工作树，依赖也可能尚未进入制品仓；直接开启 `LNGS_TESTING` 或 `LNGS_APP` 会在 CMake 配置阶段失败。不能据此把未运行的测试写成通过，也不能把消费者测试计入上游通过数。

## 触发条件

- 平台：HarmonyOS PC aarch64，Clang 15，Conan 2.29.1。
- 项目：核心库、CLI app 与测试目标共享源码树；app 依赖同族库。
- 归档：官方 tag 将 `tools/testing`、`tools/coveralls` 记录为 git 子模块，codeload 源码包不包含子模块内容。

## 根因与实测证据

mbits-lngs 0.7.6 官方源码 SHA-256 为 `85c9fd3afd5b6d5446a294f4de11221ae7fa160a62d1115a7ea0c1af17633a0b`。初次配置因精确版本的同族依赖与空子模块失败。经核验官方 `.gitmodules` pin 后，按上游源代码构建缺失依赖，并恢复精确子模块提交，随后在 HarmonyOS 真机启用 `LNGS_APP=ON`、`LNGS_TESTING=ON`、`LNGS_LINKED_RESOURCES=ON` 完成测试：

| 依赖/子模块 | 上游提交 | 源码归档 SHA-256 |
|---|---|---|
| mbits-args 0.12.3 | `72f5f2b87ae39f26638a585fa4ad0b96b4152ae6` | `1a1dc5793e927a7f8c34b77c776b4d4a88f7ce9557657d8e806fca2922bd07a0` |
| mbits-diags 0.9.6 | `20d32182f0d9b0ec49c56729add28d5200fc5596` | `db86aa0c4ce1bbfa548a39e046b7872e6f369d668ee433dc5a57cf2a026deb4c` |
| mbits-utfconv 1.0.3 | `385a8cc4d86bbf601375cf27ecb6bf9819a58afd` | `2077e3dcb999dc76d2bdc06cc141b38e10f15762975c261f72cc1a8c2519a27a` |
| mbits-mstch 1.0.4 | `3e532ca559e4eebb360172a450b13b22b1fcb13b` | `ee3052b9c2321b46fffabb5db5d5659e5f963070cdfd0004701b515867ed6857` |
| tools/testing | `0fd6cc19bc269ff436cc8339a576dba351fed42c` | `01d595c66172bca405312440eaf7df7915d35e2a7600fcf98717f2f0bd9d8f92` |
| tools/coveralls | `3e0701f6a4c0faa5e06c00d8ffe652cb3004b6b0` | `3b67cd44819b7f32075221da9862244dd15527eaefe86203e06041acb9a81e10` |

源码清点命令：`grep -R -n -E '^[[:space:]]*(TEST(_P|_F)?)[[:space:]]*\(' <源码>/libs/liblngs/tests <源码>/app/tests`。49 个 GoogleTest 声明（库 25，app 24）全部在 HarmonyOS 真机实例化并通过；两个测试可执行文件分别报告 196/196、206/206，共 402/402 参数化测试实例通过。另行运行 `ctest --test-dir <build> --output-on-failure`：CTest 的 20 项中 18 项通过，`0028-no-shared-data-enum.json` 按上游 `skippable: true` 标记跳过，`0027-no-shared-data.json` 失败；失败项将 `--share .` 放在命令名前，实际输出为 `unknown command: --share`，而 fixture 预期 `command missing`。该 CLI fixture 结果独立于 49 个 GoogleTest 声明，不从 49/49 中隐藏，也不计入通过数。

此前只执行 plurals/strings 子集：7/7 个已选声明用例通过（94 个参数实例），相对上游全部 49 个声明为 7/49 覆盖；这组旧结果已被完整复测取代。完整依赖与子模块补齐后，全量 GoogleTest 为 49/49 声明、402/402 参数实例通过。Conan `test_package` 消费者测试另计 CTest 2/2，不计入上游 49 项；包含 n=0/1/2/5 边界求值与共享消费者运行检查。

## 推荐做法

1. 先记录精确依赖版本、官方提交和归档摘要；检查 registry。若依赖尚未发布但有官方源码，可在目标真机上按精确提交自行构建并保留构建证据；不可用空桩替代。
2. 从上游 `.gitmodules` 还原 pinned 子模块，核对提交，不把子模块目录存在误当作内容完整。
3. 用项目支持的完整配置启用应用与测试。对路径、模板资源等配置逐项验证；遇到整组空输出时先查运行时资源配置，不能立即归因于代码或依赖。
4. 分开报告 GoogleTest 声明数、实际实例数、命令行 CTest、Conan 消费者测试；只把实测的通过数写入相应统计。
5. 将本地临时依赖构建与可供远端 CI 使用的 registry 依赖区分开。若 CI 仍无法解析依赖，应单独报告 CI 状态，不把本地实测表述成 CI 已通过。

## 禁止做法

- 关闭 `LNGS_TESTING` 后将 49 项写成通过。
- 把消费者测试计入上游通过数。
- 用空桩伪造缺少的测试框架或同族库。
- 因默认外置模板未安装而出现空输出，就把相关测试统计为真实失败；应先以项目支持的内嵌资源配置复跑，并保留两种配置的区别。
- 把 GoogleTest 49/49 扩大表述成所有 CTest 目标全绿；命令行 fixture 结果应独立披露。

## 查重与边界

- **E150（子模块缺失）**：聚焦手动获取或声明子模块源码。本条增加同族依赖的真机源码构建和完整测试恢复证据。
- **E425（空子模块占位）**：聚焦 SDK 子模块内容缺失。本条强调 pinned 子模块恢复后重新生成并执行 app 与库测试。
- **适用边界**：依赖源码不可取得、许可不允许本地构建，或 ABI 与目标平台不兼容时，不得宣称依赖已补齐；如只能运行子集，需保留完整分母并具体写明未运行范围。

## 元信息

- 上游：<https://github.com/mbits-os/lngs/tree/v0.7.6>
- 配方：`archives/m/mbits-lngs/0.7.6/`
- Contributor ID：328
- 状态：草稿，待知识库编辑审核
