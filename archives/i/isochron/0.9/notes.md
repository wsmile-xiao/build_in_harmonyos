# isochron 0.9 适配笔记

## 任务信息

- 平台任务号：7532（活动：开源鸿蒙PC专项积分赛-依赖；主号名额超限，经小号中转 relay 认领）
- 分支：feat/isochron-0.9；worktree：~/qzy/glm56-isochron-0.9
- 上游：https://github.com/NXP/isochron tag v0.9（tarball sha256 ab4bf84c…899c）
- 语言：C（任务登记 cpp 为 SCT 误标；lang-preflight 以文本特征判 cpp 通过——实际交付物为 C 源码，本笔记如实更正）；构建系统：内核风格纯 Makefile
- 主理 agent：GLM-56（2026-09-19）

## W0 依赖检查

- 精确版本依赖：libmnl/1.0.5（ohpcd 制品仓已发布，`conan list` 实测确认）。
- 其他链接依赖：-lm -pthread（libc 内建）；rtnetlink/SO_TXTIME 等为内核接口，运行时能力依设备内核，不影响编译链接。
- 构建工具：上游 `all` 目标用 pandoc 生成 man 手册——OHOS 无 pandoc，配方只构建 `isochron` 目标并以 `install-binaries install-completion` 安装（跳过 man）。

## W0b 历史经验

- 仓库无 isochron 历史归档，首次适配；recipe-search 无同包配方。
- 本任务踩坑均为知识库已沉淀模式的新实例：E386 getcwd（§12.38）、E017/E002、cpp_info 相对路径拼包内绝对路径（§12.38）。

## 上游测试清点（R51 证据）

上游 Makefile 为内核风格：目标仅有 all/isochron/man/clean/install*，无 check/test 目标，无测试框架；`C=1` 为 sparse 静态检查开关（非测试）。**上游静态测试数 N_static = 0**（如实申报）。

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | Makefile 目标清点 |
| 构建系统注册 N_registered | 0 | 无上游测试资产 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（2 断言） | test_package/test.sh |

## 消费者测试设计

`test.sh` 经 conanrun 环境（VirtualRunEnv 解析打包的 libmnl 动态依赖）真实运行打包产物：

1. 无参数运行 `isochron`，断言输出含 `isochron usage:`（程序五子命令用法页）；
2. `isochron daemon --help`，断言输出含 `isochron-daemon usage:`。

注：上游约定 usage 页在无参/未知参数时打印并返回非零退出码（EINVAL 22 / 255），
为 0.9 版真实行为，断言以输出内容为准、退出码不作断言。功能级链路（SO_TXTIME
时间戳收发）需要 TSN 网卡与特权内核接口，CI 环境不可达，不纳入断言。

## 源码修改

三个 portability 补丁（详见 patches/ 与 conandata.yml，strip: 1）：

1. `patches/0001-musl-pthread-affinity.patch`——src/send.c：musl 无
   `pthread_attr_setaffinity_np()`（隐式声明 + 链接失败实证）；`__GLIBC__` 守卫，
   musl 路径改 `sched_setaffinity(0, …)` 设置调用线程亲和性，sender 线程创建时继承；
   边界：主线程同时被钉住（已在补丁注释与 notes 说明）。
2. `patches/0002-musl-sysroot-includes.patch`——src/sk.c：`<time.h>` 先于
   `<linux/errqueue.h>`（SDK 26 errqueue.h 使用 struct timespec 但不自含声明，
   报 incomplete element type）；`<sys/poll.h>` → `<poll.h>`（musl 重定向
   #warning 被 -Werror 升级为错误）。
3. `patches/0003-posix-toolchain-deps-probe.patch`——Makefile：`./toolchain_deps.sh`
   无 shebang，OHOS 的 sh exec 返回 ENOEXEC（表象 "No such file or directory"），
   特性探测静默失败 → 缺 `-DHAVE_TX_SWHW` → common.h 回退宏与 SDK 26 内核头
   `SOF_TIMESTAMPING_OPT_TX_SWHW` 重定义。改为显式 `sh ./toolchain_deps.sh` 调用。

配方级（非源码补丁）平台防御：

- OHOS SDK 26 sysroot 的 UAPI `linux/socket.h` 无条件重定义 `struct sockaddr_storage`
  （musl sys/socket.h 同名定义，无 libc-compat 守卫机制）→ generate() 写入 shim 头
  遮蔽 `linux/socket.h` 与 `linux/if_ether.h`（后者路由到 musl netinet/if_ether.h，
  保证 ethhdr 单一定义者），经 `-I` 顺序生效。libmnl/1.0.5 包在该 SDK 下直接构建
  亦会踩中，属 sysroot 缺陷而非上游代码缺陷。
- `PKG_CONFIG=/bin/true`：Makefile 对 pkg-config 缺失直接 $(error)，libmnl 标志由
  配方从 Conan 依赖图显式传递（OHOS 无 pkg-config）。
- 仅构建 `isochron` 目标（跳过 pandoc man 页），安装用 `install-binaries
  install-completion`。

## 路径 B 判断

- UAPI/musl 头冲突的 shim 遮蔽模式是本任务最有复用价值的点，但生效前提是
  OHOS SDK 26 sysroot 的具体缺陷形态，且知识库已有"设备级构建与安装产物体检
  （RPATH、shim 命令）"家族条目（经验汇总 §12.38 索引行），查重命中既有家族；
  单实例不满足跨仓库知识增量的门槛。
- 结论：**纯路径 A，不申报路径 B**。

## 构建环境

- 设备真机（OHOS aarch64），CONAN_HOME=~/tmp/ch/home-glm56-gnudos；profile ci/conan/profiles/ohos-aarch64。
- 源码下载：官方 GitHub archive URL（tag v0.9），sha256 校验。

## 验证命令与结果

- `python3 scripts/ohc-run.py conan-verify isochron 0.9`：Verdict PASS（G0-G4）。
- 消费者测试实测输出：`ALL CONSUMER TESTS PASSED`。

## 已知限制

- man 手册未包含（OHOS 无 pandoc）；bash-completion 已随包安装。
- sender 线程 CPU 亲和性在 musl 下经 sched_setaffinity 继承实现，主线程一并被钉住
  （glibc 路径行为不变）。
- TSN 数据面功能（SO_TXTIME、PTP 时间戳）需设备内核与网卡支持，编译链接不受影响。

## finish 收尾块

- conan-verify：PASS（G0-G4）；W3 本地 CI：见 reports/w3-local-ci.log；W4 独立审计：提交前完成（P0/P1 清零）。
- 测试数字同源核对：notes.md = MANIFEST.yml = PR 正文 = result.json（N_static=0，N_executed=0，N_consumer=1，N_assertion=2）。
- 提交方式：精确 add archives/i/isochron/（commands.json 在软件级目录）。
---

**编译结束**: 2026-09-19 03:33
**最终状态**: built
