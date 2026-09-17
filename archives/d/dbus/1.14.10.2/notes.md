# dbus 1.14.10.2 适配笔记（fix 轮次 pc1-13，r10 版本递增）

## 任务背景

dbus/1.14.10 已有 ohpcd registry 发布（revision 2d1366526a2e661f4aa339ea87d1693c，配方与本轮基线一致，DBUS_BUILD_TESTS=OFF 仅客户端库），但缺少可运行的 dbus-daemon/dbus-run-session 会话总线能力（manifest 原 status=partial）。本 fix 轮次将其修复为完成态：产物包含 dbus-daemon、dbus-run-session 等 9 个命令行工具 + 静态 libdbus-1 + session.conf，并完成会话总线运行验证。

## 修复内容（相对既有发布）

1. `conanfile.py`：由仅构建客户端库（`cmake.build(target="dbus-1")`）改为全量构建（dbus-daemon + bus + tools）；package() 打包 bin/（9 工具）+ lib/*.a + include + share/dbus-1/session.conf；注入 `EXPAT_INCLUDE_DIR`/`EXPAT_LIBRARY`/`EXPAT_LIBRARIES` 使 dbus-daemon 链接 expat 成功（dbus 顶层 FindEXPAT 模块 vs conan expat::expat 目标不匹配）。
2. `test_package/`：test.c 改为真实消费方验证——在 DBUS_SESSION_BUS_ADDRESS 提供时完成 org.freedesktop.DBus Peer.Ping 往返；conanfile.py 测试阶段自启动包内 dbus-daemon（TCP 会话总线）注入地址后运行，断言 method return。
3. `manifest.yaml`：status partial → published，补充运行时验证与平台限制记录。
4. `commands.json`（软件级）：声明 dbus 为 tool 类型（CLI 工具 dbus-daemon/dbus-run-session 等）。
5. `reports/`：runtime-verification.md（核心门禁证据）、test-ledger.md（双口径台账）、knowledge-ledger.md（七轴查重）。

## 运行验证结果（核心门禁）

- dbus-daemon --print-address 启动会话总线并输出 tcp 地址，TCP 可达 ✓
- dbus-send --session Peer.Ping → method return, exit 0 ✓（消费方往返）
- dbus-run-session 会话内运行 dbus-send → method return, exit 0 ✓
- conan create test_package 自启动 daemon 完成 Ping → "dbus consumer roundtrip PASSED (method return)", EXIT=0 ✓

## 平台限制（真实记录，非伪造）

- OHOS 沙箱禁止 AF_UNIX bind（EPERM）→ 会话总线验证用 TCP 等价路径；恢复条件：目标设备具备 AF_UNIX 权限时用 unix:tmpdir。
- musl getpwuid_r 无运行 UID 的 passwd 记录 → 启动需用户数据库条目；验证期用 passwd shim 恢复环境。
- TCP 下 SO_PEERCRED 不可用 → 配置 allow_anonymous + ANONYMOUS 认证；AF_UNIX 恢复后 EXTERNAL 即可。

## 上游测试台账（r09 合并收敛实测更新）

源码声明 32 个测试目标，DBUS_BUILD_TESTS=ON + DBUS_WITH_GLIB=ON + glib/2.88.3 全部实例化。r09 与 main 上 goblinrs 版 1.14.10.1（commit a1345bb）同名目录合并收敛：并入 0005-dbus-daemon-link-expat.patch（dbus-daemon 链接 ${EXPAT_LIBRARIES}，与自研 EXPAT 注入双保险，patch 0001-0005 连续）、expat 版本对齐 2.8.2.1（gtk3 生态）、test_package 补 expat 库路径注入；保留本分支 DBUS_BUILD_TESTS=ON 测试能力与真实消费方往返。合并后复验：conan create EXIT=0、test-userdb rc=0、test-pending-call-dispatch 100/100 ok（服务激活）、test-ids 5/5 ok（TCP 会话总线）。

双口径：`executed_passed_total/source_declared_total = 25/32 (78.1%)`（与 r08 一致，合并未改变测试构建输入）。剩余 7 项受限均为 OHOS 沙箱 AF_UNIX/unix socket 硬限制，逐项附命令/退出码/首错/恢复条件（reports/test-ledger-r09.md）。

## 知识台账

见 reports/knowledge-ledger.md：七轴查重结论 reuse_existing=E461（根因矩阵复用）+ new_draft（dbus-daemon TCP 等价运行 + passwd shim + test_package 自启动往返组合方案）；按任务约束仅登记候选观察，知识库草稿随本库 PR 同仓交付（本轮任务无独立知识库 PR 授权）。
---

**编译结束**: 2026-09-14 11:14
**最终状态**: published
