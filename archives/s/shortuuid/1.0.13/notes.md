# shortuuid 1.0.13 适配笔记

## 当前状态

状态：pending。H1 真 Conan 包与 release 实物已核；原 G1/finish/finalize 未全过，独立 W4 为 FAIL。
当前日期：2026-09-25。

## 源码与打包

上游 PyPI sdist SHA-256：`3bb9cf07f606260584b1df46399c0b87dd84773e7b25912b7e391e30797c5e72`。
源码为纯 Python；配方复制四个模块、类型标记及 BSD 许可证，并为上游发布的 `shortuuid` entry point 安装 POSIX 命令脚本。
不修改上游源码或测试，也无新增补丁。

## 本机预检

Windows Python 3.11 上游 `unittest` 19/19 通过。
从固定 sdist 模拟包目录运行消费者 5/5 组通过。
本机未运行 Conan create；模拟包结果不可作为真机验收。

## 待验证

处理 G1 纯脚本适用性、完成独立 W4，记录全部原始退出码。已核 release tar；无 upload 或官方 CI 结果。

### 对话 #1：本地准备

2026-09-25 核对固定 PyPI sdist 与配方 SHA-256 一致，确认包内含上游测试、Python 模块和许可证。
Windows Python 3.11 已运行上游 `unittest`，19/19 通过；固定 sdist 的模拟包消费者 5/5 组通过。
本轮尚未运行 H1、Conan create、正式 W3 或独立 W4；这些结果不得写成鸿蒙适配通过。

### 对话 #2：补全上游分发命令

2026-09-25 从固定 sdist 的 `pyproject.toml` 确认上游公开 `shortuuid = shortuuid.cli:cli` 命令入口。旧候选仅测试模块调用，未安装分发命令。
新候选安装真实 `bin/shortuuid` 脚本及软件级 `commands.json`，增加实际命令编码/解码消费者；本次改动尚待 H1 Conan/W3 实测。

### 对话 #3：H1 CLI 候选原始结果

2026-09-25 从 H1 原始 tar（SHA-256 `21ad4c3aa86a1a4b2b7d43036c938f92899321dfec8cc2a6ac23aace0dffdd9b`）独立核对：固定 sdist 上游 unittest 19/19/rc0；当前 Conan create rc0，真包消费者 6/6，包括安装命令往返。原 tar 中脚本 mode 0755、模块/许可证逐 SHA 已核。
同轮 JC `prdiff(10)`/pass，W3 setup/build 各 rc0，工具 `.ci-result.json exit_code=0` 且日志 SHA 匹配；官方 G1 conan-verify rc1、整体 finish rc1、独立 finalize rc2、runner rc1。finalize 原文缺 release tar，旧 notes 状态与中间 built 不一致；软件版本索引仍空、构建日期尚未确认。W4/官方 CI 未运行，不宣称全门禁通过。
状态：pending（真实 OHOS release tar、归档一致性、G1 适用性与独立 W4 待完成）。

### 对话 #4：H1 004 真包续测与本地归档复核

2026-09-25 H1 004 package-only continuation 在原私有根、原 Conan 真包上运行：continuation/verify/package 均 rc0。回收的原 release tar 18,455 字节，SHA-256 `edece2a79dbca6d24b003b4fc9439d6b28a1b54763fd9f443ed383a1c76717f5`，恰七个普通 payload 逐 SHA 与 H1 Conan 包一致，`bin/shortuuid` mode 0755；003 续测仅因 H1 `id: bad uid 20020084` 诊断失败，无 verify/package 调用。
原 H1 conan-verify G1 rc1、整体 finish rc1、原 finalize rc2 和 runner rc1 均保留。用原字节 release tar、真实测试报告及当时的 built 元数据在 Windows 隔离归档运行未修改官方 `finalize-archive`（`PYTHONIOENCODING=utf-8`）rc0；该本地归档复核不改写 H1 旧失败。独立 W4 将最终候选的 built 状态判为 P0：真机 Conan 包及 release 已生成，但完整门禁未过，故当前候选退回 pending。
状态：pending（实际产物已核；G1/原 finish、W4 与官方 CI 仍未通过）。
