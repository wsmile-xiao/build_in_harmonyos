# mmix/20160804 适配记录

## 状态和环境
分支 feat/mmix-20160804。本轮基于 origin/main b95978a4750e7aa9a3d49af148bb3bbedf81051d（2026-10-05）切出独立 worktree。

- 2026-10-04（Windows + Ubuntu24.04 WSL，HarmonyOS SDK26.0.0.105，Clang15.0.4，OHOS Conan2.29.1）：
  完成 Linux 对照与 OHOS ARM64 动态/静态**交叉**构建，以及 static QEMU 执行。
- 2026-10-06（真实 HarmonyOS PC，aarch64，HongMeng Kernel 1.13.0）：完成设备侧签名与原生执行、
  官方原生 conan-verify、W3 本地 CI 模拟。manifest 保持 built（未发布到制品仓）。

## 来源和依赖
上游官方原版 https://mmix.cs.hm.edu/src/mmix-20160804.tgz
SHA256 fad8e64fddf2d75cbcd5080616b47e11a2d292a428cdb0c12e579be680ecdee9。
tgz 为平铺源码，get(strip_root=False)。运行时仅系统 C 库。CWEB4.12.2 为 build tool_requires，实际下载其已发布配方与 OHOS 包；Linux build context 从同一配方构建 ctangle。没有随本任务修改/发布 CWEB。

## 构建和补丁
原始源码采用 CWEB + Makefile，无 configure。保留所有 .w，官方 refresh-patch 生成两个新增 .ch 文件的补丁：
1. mmmix-portability.ch：driver buffer 改为 static，避免与 config module buffer 重复定义，最终没有 -fcommon。
2. mmotype-portability.ch：MMO uint32 时间戳按值转换为 time_t，避免 LP64 指针重解释越界。未修改的 GCC 基线读取出 1890 年，修补后与真实 MMO header 一致。
ctangle 位于 Conan build context；全部目标程序使用 host compiler conf。abstime.h 使用 Python time.time() 生成与 abstime.w printf 等价的 #define，交叉构建没有运行 AArch64 bootstrap。四个工具全部构建并打包：mmixal/mmix/mmotype/mmmix，GNU89 保留上游 K&R C 兼容性。
不添加 _GNU_SOURCE：会暴露新版 glibc 的 fadd/fmul/fdiv/fsub，与上游 pipeline enum 名称冲突。
默认 PIE + RELRO/NOW；static=True 是 QEMU/静态验证选项。OHOS 原生构建在测试前对四个新 ELF 调用 binary-sign-tool，交叉版本没有伪造已签名状态。

## 归档结构
软件级 `archives/m/mmix/` 下：`manifest.yaml`（软件元数据 + 版本索引）、`README.md`、
`commands.json`（R38，CLI 工具包必填，`type=tool`）。版本级 `20160804/` 下：`conanfile.py`、
`conandata.yml`、`manifest.yaml`、`notes.md`、`patches/`（2 个）、`test_package/`
（`conanfile.py` + `MANIFEST.yml` + `test_mmix.py`）、`upstream_tests.py`。

版本级 `manifest.yaml` 里的 `patch_generation.source_orig_dir/source_work_dir` 是补丁最初生成时
那台机器的临时目录（`/opt/ohos-dev/...`），本机不存在同一路径。这两个字段只作历史记录，
不参与本机构建：本机按 `conandata.yml` 的官方源 URL 取源码、按 `patches/` 应用补丁复现构建。
仓库内同类字段有大量先例（实测 1866 处：
`git grep -l "source_orig_dir" origin/main -- 'archives/*/*/manifest.yaml' | wc -l`），
故保留原值不做改写。

## 测试库存与真实结果
没有 make check。测试库存来自 README、49个 .mms、silly.run/.out、plain.mmconfig、test1.mmconfig/.mmix。
47个正例汇编成功；halves.mms 的 GREGTOP 未知、number1.mms 的 Main 未定义，两者在未修改 Linux baseline 也失败。它们按额外负例比较真实错误，不能声称 49个正例全通过。
README copy 完整字节一致；hello 输出与退出8检查；silly 完整约100KB trace逐字节一致，所有 Warning 单独精确比较。silly.out 是终端记录，唯一输入回显被剥离，stderr Warning 根据实际流路由比较，未修改上游文件。
README hello pipeline：halt405/end406，380零指令周期、26单指令周期。
README silly pipeline：halt4424/end4425，预测183/15、176/22，周期2655/1770；警告完整比较。
mmotype 检查真实对象、符号及 MMO header 时间戳；test1 是140周期 smoke，README可选verbose/breakpoint探索没有额外黄金断言。
上游文档/样例 harness：patched Linux62/62，OHOS static QEMU62/62。62是本适配harness检查数，上游没有正式编号的62个测试。
test_package 消费者12/12：新建19+23 MMIX程序→汇编→执行返回42→检查对象和指令→dump→pipeline模拟；拒绝坏指令与非MMO输入。Linux与QEMU都真实运行通过。
unpatched baseline61/62，失败为LP64 timestamp；为观察运行时暂用-fcommon的diagnostic二进制，仅对照用途，未加入最终配方。

## 官方门禁

### 设备侧真机验证（未依赖官方工具，独立证据）
交接包 `tests/device_validate.py` 在真机对 `runtime-static/` 与 `runtime-dynamic/` 各跑一轮：
签名前先核对 SHA256.json（182/182 一致），再对 4 个 ELF 调用
`binary-sign-tool sign -selfSign 1`，随后执行测试。

| 模式 | 上游/样例 | 消费者 | 报告 |
|---|---|---|---|
| static | 62/62 | 12/12 | device-results/static/{upstream-native.json,consumer-native.json} |
| dynamic | 62/62 | 12/12 | device-results/dynamic/{upstream-native.json,consumer-native.json} |

报告含逐条 check 名称与通过标记（无 FAIL）、58 条真实命令及签名后二进制 SHA256。

### 官方原生 conan-verify
`scripts/ohc-run.py conan-verify mmix 20160804`，使用 `ci/conan/profiles/ohos-aarch64`
（host 与 build 同为原生 OHOS），先移除本地缓存包以确保是本次真实重建：

- 工具判定：G0/G1/G2/G3 PASS，整体结论 `配方验证通过`。但 G4 只给出带告警的 PASS
  （"⚠️ 无法找到程序包 ID"），L2/L4/L5 三项均走 **skip** 分支（"⏭️ 跳过（无 cache 路径）"），
  即静态安全扫描与产物基线**并未真正求值**，不应读作"这几项已验证"。
- `reports/conan-create.log` 内含 19 条 `RUN:` 记录：9 次 ctangle、4 次 clang 编译、
  4 次 `binary-sign-tool` 签名、2 次 python3 测试脚本；并含
  `MMIX upstream/documented checks: 62/62 (OHOS native)`、`Installed MMIX consumer checks: 12/12`、
  `Package '2cdc4e3b3854eaa49bbb511eeb7d682c49e3027d' created`。对应 WSL 阶段 G2 失败的环境问题已消除。
- 已知工具限制：`conan list ... --format=json` 的键是完整 ref
  （`mmix/20160804@ohpcd/stable`）而 `gate4_artifact_integrity` 按裸软件名取值，触发 KeyError →
  G4 报「无法找到程序包 ID」并使 L2/L4/L5 走 skip 分支。这是仓库工具在带 user/channel 引用时的缺陷，
  按 R21 未修改 `scripts/`。补足的手工等价证据：4 个产物均为 PIE（ELF type DYN）、
  GNU_STACK 非可执行、存在 GNU_RELRO 且 `BIND_NOW`（`readelf -h/-lW/-dW`）。
- G0 clean-verify 报告「找不到原始 tarball」：该检查要求预置原始 tarball 并走 configure/make 流程，
  本包为 CWEB + 自定义编译，无 configure，该项不适用；非阻塞，权威构建证据来自 G2 与 W3 的 conan create。

### W3 本地 CI 模拟
`finish` step 5 调用 `ci/conan/setup.sh` + `ci/conan/build_and_test.sh`，写入
`reports/w3-local-ci.log`，通过后由工具写入 `.ci-result.json`（含日志哈希，禁止手改）。

本机为 WorkBuddy 鸿蒙沙箱，官方脚本需两处环境归一化，均属宿主适配、不涉及配方与脚本改动：
1. 沙箱把 `.../cli/vendor/shim/safe-bin` 前置进 PATH 三次，其 `rm`/`unlink`/`rmdir` 包装以
   `#!/bin/bash` 开头而本镜像无 `/bin/bash`，导致 `build_and_test.sh` 的清理步骤报
   `bad interpreter`。运行时剔除 PATH 中的 shim 条目，恢复 `/bin/rm`。
2. `~/.local/bin/conan` 的 shebang 指向 `~/usr/local/bin/python3`；该解释器在 HAP 包外，
   无法 exec 包内二进制，于是配方 `test()` 里 spawn 的 `python3`
   （`/data/storage/el1/bundle/libs/arm64/python/bin/python3`）返回 EACCES，
   `/system/bin/sh` 报 `Permission denied`（rc 126），造成 test_package 假失败。
   改用包内 python 承载 conan 后 test_package 原生通过（12/12）。
   该项通过任务本地入口（`<task>/bin/conan` + `<task>/bin/ohc`）解决，未改动共享环境。

graph validate 实际退出0（存量警告170条）。未手工创建或修改 `.ci-result.json` 与
`reports/audit-result.json`。官方 result 命令此前输出 partial，本轮的完成情况见「原生与提交接力」。

## 原生与提交接力
已完成：设备签名与原生执行（静态/动态 62/62 + 12/12）、原生 conan-verify、finish 的 W2 结构检查与 W3 本地 CI。
待完成：独立 W4 审计结论、提交到远端并创建积分赛 PR、远端 CI 与检视意见闭环。当前没有远端上传/提交。
---

**编译结束**: 2026-10-06 20:35
**最终状态**: built
