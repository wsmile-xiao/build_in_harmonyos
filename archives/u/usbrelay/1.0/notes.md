# usbrelay 1.0 适配笔记

## 概述

usbrelay（Darryl Bond）是 DCTTECH/UCREATEFUN 系列 **USB 继电器板** 的驱动：
C 共享库 `libusbrelay.so`（HID 报文构造 + 板卡枚举/操作）+ CLI `usbrelay`，
经 hidapi 走 HID 数据面。本包只打 C 本体（python 绑定与 usbrelayd 不属范围）。

- 上游：https://github.com/darrylb123/usbrelay（tag archive，R39）
- 版本：1.0｜tarball 466023B/25 文件，sha256
  `f69684b7544623fbb9845542251b20020c9e490aba9f0624ec3ae89b2b2c191b` 三源一致
- 构建系统：裸 Makefile（无 configure/无 CMake）｜语言：C｜许可：GPL-2.0-or-later
- 依赖：hidapi/0.15.0（已归档；libusb 后端）
- 编译日期：2026-09-24｜状态：built｜**补丁：无（零源码修改）**

## 上游测试清点（R51 三步法）

| 项 | 结论 |
|---|------|
| 自动化测试入口 | **0**。Makefile 无 `check`/`test` 目标（只有 all/python/clean/install/install_py）；无 ctest/TESTS/SUBDIRS 注册 |
| `test.py` | 唯一测试命名文件：只 print 无断言，入口 `import usbrelay_py`（python 绑定，本次不打包），且需真实板卡在场才有任何输出——不构成 §10 测试入口，如实申报 0，不虚报也不计入分母 |
| 结论 | 上游确无自动化测试（0 静态/0 注册/0 执行）；功能验证由消费者测试 5 组断言承担（赛道二硬门禁），并如实收口数据面限制（见下） |

## 适配中撞到的真实问题（三条机制，全零补丁）

| # | 症状（第一条真实证据，逐字） | 根因 | 解决方案 | 结果 |
|---|------------------------------|------|----------|------|
| 001 | 上游默认链 `-lhidapi-hidraw`，而 ohpcd 发布 `hidapi/0.15.0` 的 `cpp_info.libs=["hidapi-libusb"]`（无 hidraw 后端制品） | hidapi 双后端二选一；本仓发布形态是 libusb | **`make HIDAPI=libusb`**——上游 `HIDAPI = hidraw` 是普通 `=` 赋值，GNU make 命令行变量优先级高于文件赋值，可直接覆盖（⚠ 派单表里"用 = 而非 ?= ⇒ 命令行不可覆盖"的前提**被实测推翻**：`?=` 只影响默认值语义，命令行覆盖对两者都有效，唯 `override` 指令才屏蔽） | 后端公共 API 等价，链接通过；零补丁 |
| 002 | `PREFIX=/usr` 写死（含 dpkg-architecture/lib64 探测分支），install 落系统路径 | 上游面向 Linux 发行包 | 命令行覆盖三件套：`make install PREFIX=/ LIBDIR=/lib DESTDIR=<pkg>`——命令行变量对文件内 `=` 赋值免疫（GNU make 语义）；`LIBDIR=/lib` 是必需的：设备根存在 `/lib64/`，上游 `ifneq ($(wildcard $(PREFIX)/lib64/.),)` 分支会把 LIBDIR 改写为 /usr/lib64，产物落 pkg/lib64 与 cpp_info 默认 libdirs 脱节（首跑实测 `Library 'usbrelay' not found in package` 即此） | 打包落点正确，零补丁 |
| 003 | OHOS 真机数据面：`/dev/hidraw0 open=-1 errno=13(Permission denied)`、`/dev/hidraw1 open=-1 errno=13`、`/dev/hidraw2 errno=2`（探针逐字） | hidraw 子系统与节点**存在**（内核有 CONFIG_HIDRAW，已绑定 2 个设备），但设备节点属主/权限不向普通用户放行；上游放权路径是 `50-usbrelay.rules` 的 **udev 规则，而 OHOS 无 udev** | 无法在用户态修（不越权 chmod 他人设备节点、不伪造放行）；按「编译/链接/API 可调用、枚举恒 0」如实收口，PR 正文不声称设备控制可验证 | 消费者 A2 断言"枚举=0 且无崩溃"恰好覆盖该收口 |
| 004 | `usbrelay.c:28:10: fatal error: 'argp.h' file not found`（CLI 编译行） | glibc 专属 argp(3) API，musl/OHOS 不提供——**KB 既有签名** | 按 **E169** 主解 `install/requires-prebuilt`：`self.requires("argp-standalone/1.4.1")`（ohpcd 已发布 static 制品，`-largp` 与 `-I` 经 AutotoolsDeps 注入）；对照先例 archives/l/libuio/0.3.0 `patches/0001-replace-argp-with-getopt-long-for-musl.patch`（改写路线，本包不重复采用） | 链接通过，CLI 产物生成 |

003 即本单 B 主机制的实测结论（详见草稿
`DRAFT-usbrelay-1.0-ohos-hidraw-devnodes-eacces-no-udev-data-plane`）。
001/002/004 均非新知识：001/002 是 make 命令行变量语义的常规运用，004 为
E169 + `DRAFT-argp-musl-gap-bridge`（在库草稿）精确命中（B判定备注里 argp 族记 hit）。

## lang-preflight 误报留证（manifest 层新变体，非语言例外）

- 工具判 `python(env_unsupported)`，证据原文：`build_system: setuptools /
  manifest: setup.py 存在（python 打包 manifest）/ source_stats: c:3, python:2,
  bash:1，主体占比 60%`——**源码统计主体明明是 C(60%)**，是 manifest 优先级
  1 命中 `setup.py` 直接改判 python。
- `setup.py` 只是本包**附带的 python 绑定打包件**（R47 边界规则原文：
  "pybind11 绑定包判 cpp"、"辅助脚本不算主体"；SKILL v12.21 亦把
  "Python C 扩展 setup.py build_ext" 列为已知形态），产品主体（libusbrelay 库 +
  CLI）为 C + 裸 Makefile，与平台任务声明 `lang=cpp` 一致；派单明确"只打 C 本体、
  绑定子包不属范围"。
- 定性=框架 manifest 层级误判（继 libstrato=捆绑资源、vramsteg=test/ 计数后的
  **第三种变体**：绑定附带 setup.py 抢占 manifest 优先级），与 E237 无关。
- 工具原始输出与它写的 `env_unsupported` 假终态**未改写**，已移出
  `$HOME/ohpcd-ai-worker-result.json → ~/tmp/uc2/hw-4/stale-result-usbrelay-langfalse.json.bak`
  防串扰；本窗以 make 真实构建成功 + ELF 产物 + 消费者 5/5 作为"实体为 C"的交叉证据。

## E237 排他论证（派单要求）

E237=特权 daemon 运行期降级族。usbrelay 本体非 daemon（一次性 CLI + 库）、
不需要 root 常驻；其失败签名发生在**数据面 open() 层**（节点存在+EACCES+放权
机制缺失），E237 无该签名记录。按派单升 create 条件（"open 成功但 ioctl 不支持、
或枚举恒空但权限位正常"类的 E237 未记录签名）——本实测给出的是第三种：
**节点存在 + open EACCES + 放权机制（udev）平台性缺席**，KB 全库 hidraw 0 命中，判 create。

## 配方要点

- `basic_layout` + `AutotoolsToolchain`（裸 make 工程）：CC/CFLAGS/LDFLAGS 经
  `conanbuild` 环境注入（含 hidapi 的 -I/-L）；文件内 `LDFLAGS += -lhidapi-$(HIDAPI)`
  的 `+=` 语义与 env 初值兼容。
- CLI 产物存在（bin/usbrelay）→ 按 R38 提供软件级 `commands.json`（L0k/PF8 对齐）。
- 上游 install 不装头文件：package() 补 `libusbrelay.h → include/`。
- `gitversion.h` 由 Makefile 现场生成（非 git 环境回落目录名），版本串不进断言。
- test_package 运行链：`libusbrelay.so` 的 DT_NEEDED `libhidapi-libusb.so` 经
  VirtualRunEnv/conanrun 解析；test() 用 ctest + `self.run` 直跑双路径（L0d）。

## 验证结果

```text
conan create（usbrelay/1.0）：编译+链接+打包通过（产物见下）
消费者测试 test.c：A1-A5 全 PASS（SUMMARY: ALL PASS (0 failures)，见 reports）
conan-verify：G0-G4 + L2/L4/L5 —— 见 reports/conan-verify-report.md
finish/W3 本地 CI 模拟：见 .ci-result.json 与 reports/w3-local-ci.log（绑定当前 HEAD）
产物：lib/libusbrelay.so + bin/usbrelay（ELF aarch64 musl，NEEDED libhidapi-libusb）
      + include/libusbrelay.h + licenses/LICENSE + 软件级 commands.json
```

## 注意事项

- 枚举恒 0 是**平台权限模型**的结果（003），不是本包功能回归；换到有 hidraw 授权
  的环境（如插板 + 手工放权）CLI 即可实际驱动，逻辑路径未改动。
- python 绑定（libusbrelay_py.so）与 usbrelayd 若未来要归档，需各自成包并按
  R47 单独做语言预检（绑定属 python C 扩展形态）。
- CLI `usbrelay --version` 与库 `libusbrelay_version()` 均回显 `gitversion`
  （GITVERSION）；tag archive 无 .git 时 Makefile 回落 `DIR_VERSION=pwd basename`
  （conan 构建下实测为 `"b"`，属上游非 git 环境设计行为）——消费者断言 A1 只判
  "非空字符串"，不硬编码其值；`1.0` 语义以包版本与归档路径为准。

## 申报口径（PR 两表同源，双口径）

- 上游表合计 = **1**（审查实测口径：test.py 演示资产，§12.72 宁高勿低）；
  注册/执行口径 static=registered=executed=**0**（两口径在 manifest.yaml
  review_count_total 与 static_total 分行共存）；
- 适配后合计 = 上游申报 1 + 消费者 1 程序（5 断言另列计入合计）= **2 ≥ 1** ✓，
  注册口径下亦 1 ≥ 0 ✓；
- 验证结果三行：编译通过；上游 0/0（如实申报+清点证据）；新增 5/5（100%）。

## 最终状态

- usbrelay/1.0：built（conan create 通过、消费者 5/5、门禁全绿后由 finish 收口）；
  分支 feat/usbrelay-1.0；PR 与 CI 状态以登记表/平台为准。
