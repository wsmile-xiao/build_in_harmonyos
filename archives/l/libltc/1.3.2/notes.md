# libltc 1.3.2 编译笔记

## 历史记录（2026-06-02，预编译归档）

### 流程
1. init-build
2. autoreconf -i (GitHub tarball)
3. E007/E011 fixes
4. configure + make + make check (3/3 PASS)

### Status
published - 2026-06-02

## 2026-09-29 Conan 配方补齐（本轮）

### 背景
- 制品仓 ohpcd 无 libltc 任何版本（`conan list "libltc/*" -r=ohpcd` 0 条；
  `conan download libltc/1.3.2 -r=ohpcd --only-recipe` 返回 CNB 特有报错
  `error:system acceleration policy not enabled`，即"未发布"，见知识库 E477）。
  因此无需 R37 版本递增，Conan 包版本保持 1.3.2。
- 历史目录只有预编译归档格式（patches/0001-0019 为当时设备上 autoreconf 产物的 per-file diff，保留不动）。

### 本轮改动
- 新增 `conanfile.py` + `conandata.yml`：官方 release tarball
  https://github.com/x42/libltc/releases/download/v1.3.2/libltc-1.3.2.tar.gz
  (sha256 0a6d42cd6c21e925a27fa560dc45ac80057d275f23342102825909c02d3b1249)。
  release 包自带 configure/ltmain.sh/config.guess，无需 autoreconf（区别于历史用的 GitHub 归档）。
- OHOS 交叉：自带 config.guess/config.sub 为 2018 版，不识别 linux-ohos；
  按 a52dec 模式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` 绕过，无需补丁。
- 上游测试：build 阶段 `make check`（ltcencode/ltcdecode 48k/96k diff + timecode.raw 解码比对 + ltcloop 回环，全本地确定性，无外部依赖）。
- 新增 `test_package/`：CMake 消费测试 test_ltc.c（6 断言），encode 01:02:03:00 起始 2 帧再 decode 回来验证 SMPTE 时间码。

### W0 依赖结论
- 依赖数量：0（仅 libc + libm，AC_CHECK_HEADERS 全为标准头）。
- 已满足依赖：无外部依赖。
- 缺失依赖：无。不需要拆分依赖适配。

### 验证状态（诚实记录）
- 本机（Windows）已完成：py 语法检查、YAML 解析检查、源码 SHA256 复核、目录边界检查、补丁 git apply --check。
- 静态门禁自检（真机CI自检模板第一部分）：lang-preflight 通过（task=cpp detected=c）；G0e/JC/L0 逐条通过；conan-verify 因本机无 OHOS 交叉环境未跑，由真机 shadow CI 覆盖。

## 真机 shadow CI 记录（2026-09-29，设备 <真机IP>:<端口>，连接信息不入库）

job：`~/ohos-users/codex/libltc-1.3.2-20260929`，run 目录见下表。

| 项 | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|
| run 目录（时间戳） | 101444 | 102342 | 102915 | 103934 | 104705 |
| exit code | 1 | 1 | 1 | 1 | **0** |
| 失败门禁 | KC | KC | L1(conan create) | L1(test_package) | — 全过 |
| 报错原文 | `permission denied: bash` | 同左 | `configure: Permission denied`(126) → 修复后又遇 `config.status: ./confXXXXXX/subs1.awk: Permission denied` | `test_ltc.c:42: unknown type name 'SMPTETimeCode'` | — |
| 根因 | 设备 /usr/bin/bash 未签名不可执行（环境问题，非包问题） | 同左 | E232：HMDFS 拒脚本直接 exec；E011/E112：umask 077 mktemp 目录无写权限 | 本轮 test_package 类型名拼写（上游为 SMPTETimecode） | — |
| 解法 | job 副本 ci/conan/build_and_test.sh 两处 `bash`→`sh`（仅设备隔离副本，不进 PR；Linux CI 不受影响） | 同左 | conanfile 按 E232 加 settings_build.os==OHOS 时 `sh <configure>` 分支；新增 patches/0003-configure-umask-022.patch（umask 077→022，a52dec 同款） | test_ltc.c 改 SMPTETimecode | — |

r5 结果（exit 0）：
- 上游测试：`make check` 全过（r4/r5 日志确认 `libltc-1.3.2 passed all tests.`，含 ltcencode/ltcdecode 48k+96k diff、timecode.raw 解码比对、ltcloop 回环）。
- test_package：6 断言 CMake 消费测试通过（exit 0 佐证 L1 pass 含 L1e 反向验证；门禁明细 L0/L1/L2/L4/L5 文本待设备网络恢复后补取，设备 r5 完成后 ping 不通）。
- 产物：libltc.a 静态库（--disable-shared --enable-static 默认 profile）。

环境备注（进 PR 时不含设备敏感信息）：
- 设备 bash/git 二进制当前不可执行是设备环境状态，与本包无关；shadow CI 通过 job 副本 sed 绕过，Linux 网站 CI worker 有 bash 不受影响。
- 设备无 git（--repo-source 复用既有 job repo）。

### 下一步
- 设备恢复后补取 r5 门禁明细文本（L0/L1/L2/L4/L5）。
- push 分支并开 PR（`python3 scripts/ohc-run.py submit libltc 1.3.2` 或手动 push + GitCode PR）。
- 原 shadow CI 命令（已执行，r5 exit 0）：
```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job libltc-1.3.2-20260929 \
  --package archives/l/libltc/1.3.2 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/libltc-1.3.2-20260929/run-conan-heavy.sh"
```

### issue
待补：本轮未找到明确 issue 编号（用户已说明 issue 不用管）。
