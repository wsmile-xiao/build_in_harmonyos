# redir 3.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

redir 是单文件 C 程序（redir.c）的 TCP 端口重定向 CLI 工具，上游 GitHub
发布 tarball 为 git archive 快照（不含 configure 脚本），需要 autoreconf 引导：

```bash
# 源码下载（官方 tag tarball）
# https://github.com/troglobit/redir/archive/refs/tags/v3.3.tar.gz
# sha256: 7311731097aabd390bd4d8f390980278b16b25d0bae8e21a9e768cd824f846f7

# conan create（含 autoreconf -fi 引导 + configure + make -j1）
conan create archives/r/redir/3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

# 配方内关键配置
#   --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
#   --with-libwrap=no（OHOS 无 libwrap/tcpd，上游可选依赖默认降级）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机缺 automake/aclocal/libtoolize，`autoreconf -fi` 失败 | 最小 OHOS 镜像仅带 autoconf 套件 | `tool_requires("automake/1.18") + tool_requires("libtool/2.5.4")`（参考 abiword-plugin-clarisworks 先例） |
| 2 | config.guess 无法识别 HarmonyOS | uname -s = "HarmonyOS" 不在 config.guess 表中 | configure 显式传 `--build/--host=aarch64-unknown-linux-ohos`（config.sub 支持 *-linux-ohos） |
| 3 | config.status 报 `./confXXXXXX/subs1.awk: Permission denied` | E114：HMDFS 下 `umask 077 && mktemp -d` 创建 drwx--S--- 临时目录，owner 也无法写入 | 参考 E114 既有方案：build() 中删除 configure 里的 `umask 077`，让 mktemp 直接建可写目录 |
| 4 | conan-verify 模板 test_package 用 CMake find_package 链接库 | redir 是纯 CLI（bin_PROGRAMS=redir），无库产物 | 改为 application 包 + VirtualRunEnv + shell 端到端消费者测试 |
| 5 | E2E 测试监听失败 | redir 参数语法要求 `[SRC]:PORT` 必须带冒号，裸端口号 parse_ipport 返回 -1 并打印 usage | 测试脚本传 `127.0.0.1:<port>` 形式 |

## 依赖版本

无运行时依赖。构建工具链 tool_requires：
- automake/1.18（ohpcd registry）
- libtool/2.5.4（ohpcd registry）

## 验证结果

```bash
# conan-verify 8 道门禁全过（G0-G4 + L2/L4/L5）
# G2 conan create 干净构建通过
# test_package 消费者验证：
#   [1/2] redir -h → 退出码 0，打印 usage
#   [2/2] E2E TCP 重定向：本机回显服务 ← redir 隧道 ← 客户端，往返数据逐字节匹配
```

## 注意事项

- redir 是 CLI 工具（非库），`package_type = "application"`，无 cpp_info.libs；
  已按 R38 在软件级目录声明 `archives/r/redir/commands.json`（type=tool）。
- 上游无独立测试源（Makefile.am 仅 bin_PROGRAMS，无 check 目标），
  上游用例数 = 0；实际验证由 test_package 的消费者端到端测试承担。
- 构建时保持 `make -j1`（E074：HMDFS jobserver fifo EPERM）。
---

**编译结束**: 2026-09-21 03:31
**最终状态**: built
