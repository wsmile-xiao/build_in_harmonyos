# socket99 0.2.2 适配笔记

## 编译环境
- 构建系统: Makefile
- 编译日期: 2026-09-03
- 编译器: Conan `tools.build:compiler_executables:c`（clang）
- 状态: built（远端设备验证通过，待 CI 验证；尚未 upload）

## 编译步骤

上游没有 configure、Autotools 或 `make check` 目标。配方在源码目录中使用
`make -j1 all` 生成 `libsocket99.a` 和测试程序，随后运行上游实际入口
`make -j1 test`。`CC`、`AR`、`RANLIB` 和完整 CFLAGS 均由 Conan 配方显式传入。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初始化脚本将 Makefile 误判为 autotools，且当前仓库模板文件名未匹配 | 项目只有裸 Makefile；模板目录没有脚本所探测的旧文件名 | 手工编写 Makefile 配方，保留 `make test` 上游入口 |
| 2 | 公共头文件直接声明 `FILE` 与 `size_t` | `socket99.h` 未直接包含 `<stdio.h>` 与 `<stddef.h>`，消费者只包含该头文件时不自洽 | 增加最小公共头修复补丁，远端以同一 Conan 依赖图验证 |
| 3 | OHOS 上游 Unix-domain 测试 `bind()` 返回 `Operation not permitted` | 在设备用户可写目录中仍复现，属于 OHOS 文件系统 Unix socket 能力/安全限制；不是 HMDFS 单一路径问题 | `test_all` 增加 `SOCKET99_SKIP_UNIX=1` 显式能力开关；配方仅在 `os=OHOS` 设置，保留 TCP/UDP 测试并如实记录 4 个跳过 |
| 4 | Conan `package()` 依赖上游 `make install`，但设备没有 `install` 命令 | 第二轮设备日志出现 `make: install: No such file or directory`，退出码 127；不是库编译或链接错误 | 使用 Conan `mkdir()`/`copy()` 直接安装 `libsocket99.a` 与 `socket99.h`，不扩大设备工具依赖 |
| 5 | 本地初始化的 CA 安装路径指向只读设备路径 | 初始化脚本的环境探测适用于鸿蒙设备，不适用于 macOS | 记录为本地脚本环境提示；真实 Conan 验证只在鸿蒙设备执行 |

## 源码修改

`0001-socket99.h.patch`：在 `socket99.h` 中直接包含
`<stddef.h>` 和 `<stdio.h>`，让公开 API 的 `size_t`、`FILE` 声明满足 C
头文件自包含约定。补丁由源码编辑后使用 `refresh-patch --auto` 生成。

`0002-test_all.patch`：为上游 `test_all` 增加 `SOCKET99_SKIP_UNIX=1`
能力开关。OHOS 配方设置该变量以跳过设备明确不允许的文件系统 Unix socket
测试；非 OHOS 构建不设置，仍运行上游全量测试。

## 依赖版本

无 Conan 编译依赖；设备工具链版本、Conan profile 与远端执行路径在报告中记录。

## 验证结果

```text
第一轮远端验证中，`make -j1 all` 通过；未打补丁的 `make -j1 test` 中
TCP/UDP 6 个角色通过，Unix stream/datagram 4 个角色在 `bind()` 因 OHOS
限制失败（每组各包含 client/server）。将相同测试程序复制到设备用户可写目录复跑，仍为同一
`Operation not permitted`。第三轮修复后，`conan create --build=missing`
完整通过：`make all` 编译静态库和上游测试程序，`SOCKET99_SKIP_UNIX=1 make
-j1 test` 中 6/10 个上游角色通过、4/10 个明确跳过；Conan `package()` 收录
`libsocket99.a` 和 `socket99.h`；`test_package` 消费者 8/8 项检查通过。
官方 URL 修复提交随后在设备端再次执行同一流程并返回 0；计数修正提交又以
`$HOME/tmp/socket99-0.2.2-w3-r8-count-fix/conan-create.log` 强制从源码重跑并返回 0。
本地 macOS 仅完成
源码、补丁、Makefile、上游测试入口和配方静态检查。
```

## 交付物

| 文件 | 说明 |
|------|------|
| `libsocket99.a` | Conan `package()` 通过 `conan.tools.files.copy` 安装到 `lib/` |
| `socket99.h` | Conan `package()` 通过 `conan.tools.files.copy` 安装到 `include/` |

## 注意事项

上游 `test_all` 以短暂后台进程配对客户端/服务端，最终 shell 状态主要来自
最后一个客户端命令；MANIFEST 按实际五组/十角色记录，并注明 OHOS 跳过 4
个角色，不虚报为 `make check`。设备端第三轮日志位于
`$HOME/tmp/socket99-0.2.2-w3-r3/conan-create.log`，最终提交复验日志位于
`$HOME/tmp/socket99-0.2.2-w3-r8-count-fix/conan-create.log`；前两轮失败证据分别位于
`$HOME/tmp/socket99-0.2.2-w3-r1/conan-create.log` 和
`$HOME/tmp/socket99-0.2.2-w3-r2/conan-create.log`。
