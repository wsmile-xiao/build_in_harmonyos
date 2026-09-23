# socket99 0.2.2 设备验证记录

## 输入与环境

- 本地 worktree: `/Users/awstme/Documents/HarmonyPC/case-sensitive-workspaces/wt-socket99-0.2.2`
- 远端 worktree: `$HOME/ws/wt-socket99-0.2.2`
- 验证提交: `f997df87efd2f628a6bb6e0344bb3f6340a700f2`
- 源码: `https://github.com/silentbicycle/socket99/archive/refs/tags/v0.2.2.tar.gz`
- 源码 SHA-256: `657907afc1e2dc42406d257cc032e97f66739c8d8873c424b567a913d3ffc36e`
- Conan: `2.29.1`
- C 编译器: `/data/service/hnp/bin/clang 15.0.4`
- Make: `GNU Make 4.4.1`
- Profile: `ci/conan/profiles/ohos-aarch64`，`os=OHOS`、`arch=armv8`、`compiler=clang 15`、`cppstd=17`

每轮均从本地推送后的功能分支执行远端 `pull --ff-only`，远端目标目录的
socket99 跟踪文件无改动；Conan 产生的 test consumer 可执行文件已从远端
worktree 删除，验证后状态恢复干净。

## 原始失败与定位

### W3 round 1: 上游测试能力限制

命令：

```sh
conan create "$HOME/ws/wt-socket99-0.2.2/archives/s/socket99/0.2.2" \
  --build=missing -pr:h="$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64"
```

日志：`$HOME/tmp/socket99-0.2.2-w3-r1/conan-create.log`。

结果：`make -j1 all` 通过；TCP 阻塞、TCP 非阻塞和 UDP 客户端/服务端共
6 个角色通过。Unix stream/datagram 两组各有 server/client 两个角色，4 个
角色中服务端 `bind()` 报 `Operation not permitted`，客户端随后因没有 socket
路径而失败。
将同一构建出的 `test_socket99` 与 `test_all` 复制到设备用户可写的
`$HOME/tmp/socket99-0.2.2-upstream-r1` 后复跑，仍在 Unix socket `bind()`
处得到相同错误，故不是 Conan cache 或单一 HMDFS 路径问题。

### W3 round 2: 打包工具缺失

在 `test_all` 增加显式 `SOCKET99_SKIP_UNIX=1` 后，Conan 构建阶段的 6 个
受支持角色通过、4 个 Unix 角色按证据跳过，随后 `package()` 报：

```text
make: install: No such file or directory
make: *** [Makefile:40: install] Error 127
```

日志：`$HOME/tmp/socket99-0.2.2-w3-r2/conan-create.log`。这是设备缺少
GNU `install` 工具，不是编译、链接或上游 socket API 失败。

## W3 round 3: 修复后结果

日志：`$HOME/tmp/socket99-0.2.2-w3-r3/conan-create.log`。

同一 `conan create --build=missing` 返回 `0`，并记录：

- 两个补丁均应用成功；
- `make ... all` 编译 `socket99.o`、上游测试程序并生成 `libsocket99.a`；
- `SOCKET99_SKIP_UNIX=1 make ... test`：TCP blocking 2/2、TCP nonblocking
  2/2、UDP 2/2，通过共 6 个角色；Unix stream/datagram 两组共 4 个角色显式跳过；
- Conan 原生打包收录 1 个 `libsocket99.a` 和 1 个 `socket99.h`；
- `test_package` 使用安装后的头文件和静态库编译消费者并运行，输出
  `socket99 consumer checks: 8 passed`。

官方 URL 修复提交 `dfd5e88a989ab02d1248b13b68c2b844ed0b4a1c` 在
`$HOME/tmp/socket99-0.2.2-w3-r4/conan-create.log` 中再次完成同一
`conan create --build=missing`，返回 `0`；该轮用于确认最新提交的设备输入
仍然一致，结果同样为 6/10 上游角色通过、4/10 跳过、8/8 消费者断言通过。

## 最终计数复核

计数修正提交 `f997df87efd2f628a6bb6e0344bb3f6340a700f2` 在设备端使用
`conan create --build="socket99/*"` 强制从源码重建，日志为
`$HOME/tmp/socket99-0.2.2-w3-r8-count-fix/conan-create.log`，返回 `0`。
源码 `test_all` 的 10 次角色调用与 MANIFEST 对账一致：TCP blocking 2/2、
TCP nonblocking 2/2、UDP 2/2，共 6 个通过；Unix stream/datagram 两组的
4 个角色未启动，统一由 `SOCKET99_SKIP_UNIX=1` 显式跳过。日志同时显示
`socket99 consumer checks: 8 passed`。

## 测试计数边界

上游 `test_socket99.c` 有 10 个返回布尔结果的角色函数，`test_all` 组织为
5 个场景组。OHOS 本次是 6/10 executed-and-passed，4/10 skipped；不能把
跳过项计入通过率。新增消费者是 1 个可执行文件、8 个显式 `CHECK` 断言，
8/8 通过。仓库的 `test_package/MANIFEST.yml` 与上述计数一致。

## 未运行项

未在 macOS 上运行 Conan/OHOS 交叉构建；未在远端执行 `make check`，因为上游
没有该目标；未声称完整 Unix-domain socket 能力，因为本设备对 pathname
socket bind 的限制只支持上述证据范围。
