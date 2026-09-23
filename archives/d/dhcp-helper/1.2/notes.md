# dhcp-helper 1.2 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile，无 configure、无 install 依赖问题）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（OHOS SDK llvm）
- 状态: built

## 编译步骤

探索阶段（设备真机，R1 探索模式）：

```bash
cd ~/builds/dhcp-helper-1.2.work
make CC=clang CFLAGS='-O2 -fPIE' LDFLAGS='-pie' version=1.2
./dhcp-helper -v
# → dhcp-helper version 1.2, Copyright (C) 2004-2012 Simon Kelley
```

配方固化（conan create 路径）：
- build(): `make CC="<profile clang>" CFLAGS="-O2 -fPIE" LDFLAGS="-pie -Wl,-z,relro,-z,now" version="1.2" -j1`
- `version=1.2` 覆盖 Makefile 的 `$(shell ./get-version)`（见问题 1）
- package(): 二进制复制到 `<pkg>/sbin/dhcp-helper`（保持上游 sbin 布局），COPYING/COPYING-v3 到 licenses/，OHOS 下 ELF 自签（connect-proxy 同款已验证方案）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-v` 输出 version UNKNOWN | release tarball 的 get-version 脚本含未替换的 `$Format:%d$` 占位符且无 .git，命中其 "unsubstituted file" 分支回退输出 UNKNOWN | make 命令行传 `version="1.2"` 覆盖（命令行变量优先于 Makefile 内定义），无需改源码/打补丁 |

## 上游测试清点（R51）

- 上游源码无任何测试资产：Makefile 仅有 all/clean/install 目标，无 check/test；
  源码包仅含 dhcp-helper.c（564 行）、Makefile、get-version、dhcp-helper.8、README、CHANGELOG、COPYING、COPYING-v3。
- 上游静态测试总数 N_static = 0（如实申报，无夸大空间）。
- 消费者测试：test_dhcp_helper.c 驱动安装后的二进制走 4 条无特权参数路径
  （`-v` / 无参数 / `-i <坏接口>` / `-Z` 未知选项），每路径断言退出码 + stderr 消息，共 8 项断言。
  四条路径均已在设备真机探索阶段实证过实际输出与退出码。
- 未执行说明：中继转发主功能需 root 绑定 UDP 67/1067 端口并配置广播接口，
  消费者测试环境不提供特权，属环境限制，如实申报。

## 依赖版本

无第三方依赖（仅 libc；musl 已内置 resolver/socket 例程）。

## 验证结果

conan-verify（2026-09-11 设备真机，8 道门禁全过，报告 `reports/conan-verify-report.md`）：
- G2 conan create 成功（日志 `reports/conan-create.log`）。
- test_package 实际执行，8/8 断言通过（日志同上，`PASS: ... × 8` + `all dhcp-helper behaviour checks passed`）：
  1. `dhcp-helper -v` 退出 0 且输出 `dhcp-helper version 1.2`；
  2. 无 `-s/-b` 退出 1 且提示 `no destination`；
  3. `-i nosuchif9` 退出 1 且提示 `bad interface`（SIOCGIFFLAGS 校验真实生效）；
  4. `-Z` 退出 1 且输出 `Usage: dhcp-helper`。
- 测试账本：N_static=0（上游无测试，如实申报）；N_consumer=1（test_dhcp_helper 程序），N_assertion=8（括注）。

## 路径 A/B 判断（§6.2，2026-09-11）

**结论：纯路径 A，不走路径 B。** 判断依据：

1. **证据门槛核对**：本次适配 G2/conan create 一次通过，全程零适配补丁、零新错误签名（唯一警告为上游既有代码现状）；无"已穷尽方案的部分适配分析"产出。
2. **拟沉淀知识主题核对**：唯一非常规操作是 `make version=1.2` 命令行变量覆盖（对策 get-version 的 UNKNOWN 回退），属 Makefile 变量优先级的常规技巧，非跨仓库复用的适配机制；ELF 自签与 sbin 布局沿用已合入的 connect-proxy 配方既有模式（非新知识）。
3. **知识库查重结论**：conan-verify G0/知识引擎未命中任何新错误模式，本次未生成任何新知识草稿（仓库既有 562 条草稿为累计存量，与本任务无关）；无新增价值点可申报。
4. **真实验证证据**：设备真机 8/8 消费者断言通过（见下），仅支撑路径 A 交付，不含可复用知识增量。

## 注意事项

- 二进制安装于 sbin/（上游布局），`cpp_info.bindirs=["sbin"]`。
- OHOS 下中继运行需 root + 接口配置，属运行环境限制，不影响配方与编译验证。
- 上游 `-Wsign-compare` 警告（CMSG_NXTHDR 循环）为上游代码现状，不属于适配问题，未修改。
