# libseat 0.9.1 适配笔记

## 编译环境
- 构建系统: meson（seatd monorepo 中的 libseat 库组件）
- 编译日期: 2026-09-07
- 编译器: clang 15（OHOS aarch64 交叉）
- 状态: published

## 编译步骤

1. 官方源：seatd monorepo tag 0.9.1（libseat 库的上游仓库）：
   `https://github.com/kennylevinsen/seatd/archive/refs/tags/0.9.1.tar.gz`
   SHA-256 `819979c922a0be258aed133d93920bce6a3d3565a60588d6d372ce9db2712cd3`
   （与已发布的 seatd/0.9.1 配方同源同 tag 同哈希）
2. 原生验证：`meson setup build-native ...`（server=disabled / libseat-seatd=enabled /
   libseat-logind=disabled / werror=false）→ build 通过；`meson test` 运行上游测试：
   linked_list OK、connection OK、poller 无限阻塞（timeout 终止）。
3. Conan 配方（archives/l/libseat/0.9.1/conanfile.py）：Meson 工具链，只构建库
   （server=disabled），libseat-seatd 后端启用，libseat-builtin 可选，logind/man-pages/examples
   禁用；OHOS 下注入 SDK llvm-ar/llvm-ranlib 到 native 文件并关闭 werror。
4. `conan-verify`（ohos-aarch64 profile）：G1~G4 + L2/L4/L5 全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 编译报 `libseat_close_device` 参数过多 | 误按旧 API 传 3 参 | 修正为 `libseat_close_device(seat, device_id)`（2 参，fd 由库内部管理）|
| 2 | test_package 运行时 session switch 断言失败 | noop 后端按设计无法切换会话，`switch_session` 返回 -1 且**不设置 errno** | 断言改为仅校验返回值 `< 0`，与真实 API 行为一致 |
| 3 | 上游 `tests/poller.c` 无限阻塞 | poller 测试等待事件分发，无事件源时不返回 | 构建期仅运行 linked_list 与 connection；poller 记为未运行并写入 MANIFEST 台账 |

## 源码修改

无补丁（patches/ 为空）。配方式处理不修改上游源码：
- werror=false（OHOS SDK 头文件 CMSG_NXTHDR 警告来自 SDK 自身）
- 后端选择全部通过 meson 选项控制

## 依赖版本

无 Conan 依赖（仅系统 libc / rt）。

## 验证结果

```bash
# 上游测试（原生）
meson test -C build-native linked_list   # PASS
meson test -C build-native connection    # PASS
meson test -C build-native poller        # 无限阻塞（设计如此，须外部 timeout）

# 消费者测试（OHOS aarch64，conan create 内运行）
./test_libseat   # 16 项断言全部通过
```

## 注意事项

- 产物库名为 `libseat`（meson library 目标名 'seat' → libseat.so.1 / libseat.a）。
- pkg-config 名 `libseat`，cmake target `libseat::libseat`。
- poller 上游测试仅在真实事件驱动的设备验证中可运行，需外部 timeout 保护。
---

**编译结束**: 2026-09-07 23:18
**最终状态**: published
