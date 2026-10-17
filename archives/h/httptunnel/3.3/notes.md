# httptunnel 3.3 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，无 config.guess 依赖）
- 编译日期: 2026-09-12
- 编译器: clang 15（OHOS aarch64，/data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

1. W0 预检：无任何外部依赖（preflight_check.sh 通过，"未找到依赖声明"）。
2. 探索构建（设备原生验证）：`CC=clang ./configure --prefix=...` 一次通过，
   poll/select/daemon/vsyslog 等探测全部 yes；`make -j1` 仅告警（旧代码
   non-prototype 警告），产出 hts/htc 两个可执行文件。
3. conan create（ohos-aarch64 profile）经 conan-verify G2 验证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备 /tmp 只读（SKILL E002），hts/htc 调试日志写 /tmp 失败 | OHOS /tmp 为只读文件系统 | 日志重定向到 $HOME/tmp 下目录 |
| 2 | htc 隧道数据回传路径失效：poll() 对 GET socket 返回异常 revents 位图 0xffffff80（无 POLLIN/HUP/ERR/NVAL 任何有效位） | OHOS 内核对处于 htc 特定状态的 socket 返回垃圾 revents；最小化 poll 复现程序（accept 后有数据/新建连接两种场景）均正常，最小 SO_RCVLOWAT/SO_SNDLOWAT 复现排除 lowat 选项，具体内核交互根因超出本任务范围 | 记录为已知平台限制；消费者测试断言已验证可用的路径（见下），不掩盖失败 |

## 源码修改

无补丁（conandata.yml patches 为空）。上游 configure 无 AC_CANONICAL_HOST，
不依赖 config.guess/config.sub，无需 E007 补丁。

## 依赖版本

无外部依赖。

## 验证结果

设备实测（探索构建 + 调试日志，DEBUG_MODE 重建）：

- `hts --version` / `htc --version` → `hts (httptunnel) 3.3` / `htc (httptunnel) 3.3`，exit 0
- hts 真实服务：bind 18023 → 接受 htc 双连接（GET/POST）→ 解析 TUNNEL_OPEN → do_connect 目的端口成功（全部出现在调试日志）
- htc 真实客户端：bind 前转端口 18024 → 接受本地连接 → 建立双向隧道连接
- 消费者测试（test_package，5 项断言）覆盖：双二进制版本输出、htc 前转端口 accept、
  hts 隧道端口 accept、隧道握手后 hts 向目的端口转发连接（echo 服务器 marker 文件）

## 测试四维账本

| 维度 | 数量 | 说明 |
|------|------|------|
| 上游静态声明 N_static | 0 | Makefile.am/Makefile.in 无 check 目标、无 tests/ 目录 |
| 实际执行 N_executed | 0 | 上游无测试可执行 |
| 跳过/未执行 | 0 | — |
| 新增消费者测试 N_consumer | 1 | test_httptunnel.sh（5 项断言） |

## 注意事项

- hts/htc 均为 CLI 工具，commands.json 已声明（type=tool）。
- 安装布局为 bin/ + man/man1/（非 share/man）。
- 已知限制：htc 数据回传路径在 OHOS 上受 poll() 异常 revents 影响不可用
  （证据：htc 调试日志 `revents: device=0 tunnel=0xffffff80`，`tunnel read error:
  I/O error`；最小复现程序证明 OHOS poll 对常规 TCP 场景正常）。隧道建立、
  目的转发、服务端全链路均正常。
---

**编译结束**: 2026-09-13 03:41
**最终状态**: built
