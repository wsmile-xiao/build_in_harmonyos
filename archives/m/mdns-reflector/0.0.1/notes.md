# mdns-reflector 0.0.1 适配笔记

## 任务信息

- 分支：`feat/mdns-reflector-0.0.1-codex`
- worktree：`D:\harmonyos\worktrees\mdns-reflector`
- issue：待补（本轮指示忽略 issue 查询）
- 上游：https://github.com/pbkhrv/mdns-reflector （作者 Yuxiang Zhu）
- 许可证：GPL-3.0-or-later（源码 COPYING 为 GPL-3）

## 版本与源码钉定

- 上游**没有** git tag / GitHub release；`0.0.1` 来自上游 `mdns-reflector.spec`
  的 `Version: 0.0.1`（二进制 banner 为 "0.0.1-dev"）。
- Debian/Ubuntu 打包 `0.0.1+git20230914.4b4cd3b-2.1` 使用的 commit 即
  `4b4cd3b196f09b507d9a32c7488491bbd5071ba6`，本配方钉定同一 commit：
  - URL: https://github.com/pbkhrv/mdns-reflector/archive/4b4cd3b.tar.gz
  - SHA256: `e4a95915876576888f2f5e4efd51393e591cf7c0999afaae3331be4e8828bc05`
  - 归档 25643 字节，根目录 `mdns-reflector-4b4cd3b196f.../`，`strip_root=True` 解包。
- URL 带 `.tar.gz` 后缀（规避 codeload 无后缀被当 zip 的坑，xmodem 经验）。

## W0 依赖结论

```text
依赖数量：0（纯 C，仅 libc）
已满足依赖：全部（无第三方运行时/构建依赖）
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无
下一步：直接进入 W1
```

源码 include 清单（全部 6 个 .c 文件核对）：stdlib/stdio/string/errno/unistd/
libgen/syslog/signal/fcntl/sys stat/param/socket/ioctl/netinet/in/arpa/inet/net if/
sys/epoll（`__linux__` 分支）。无 pthread、无第三方库，CMakeLists 无 find_package。

## W1 源码/构建系统分析

- 语言：C11，构建系统 CMake >= 3.14（`cmake_minimum_required(VERSION 3.14)`）。
- 产物：单个可执行文件 `bin/mdns-reflector`（application，无库文件）。
- 事件循环：`reflector.c` 按 `#if defined(__linux__)` → `<sys/epoll.h>`；
  `#elif defined(__unix__)||defined(__APPLE__)` → `<sys/event.h>`(kqueue)。
  OHOS clang 定义 `__linux__`，走 epoll；musl 提供 epoll_create1/epoll_ctl/epoll_wait。
- 平台风险点（低）：
  1. `u_int32_t`（BSD 类型，main.c 的 MDNS_ADDR4）——musl sys/types.h 提供
     u_int*_t，预期可用；若 CI 报 unknown type 再按知识 E113 处理。
  2. `MCAST_JOIN_GROUP`/`struct group_req`（RFC 3678）——musl netinet/in.h 定义
     该宏；且代码有 ipv6_mreq/IP_ADD_MEMBERSHIP 的运行时 fallback。
  3. `syslog(3)`——musl 提供；OHOS 上 /dev/log 可能不存在，最多无日志输出，
     不影响编译与 -h 冒烟。daemon 模式（-d）才依赖 fork/setsid。
  4. `SO_BINDTODEVICE`/`IP_PKTINFO`/`SO_REUSEPORT` 均有 `#if defined(...)` 守卫。
- 编译选项 `-Wall -Wextra -Wpedantic -Wconversion -D__APPLE_USE_RFC_3542`：仅警告，
  无 `-Werror`，交叉编译下不会因警告失败。

## 上游测试清点（R51 证据）

上游**未附带任何测试**：

- 源码树无 `tests/`/`test/` 目录（归档清单：.dockerignore .gitignore CMakeLists.txt
  COPYING Dockerfile README.md debian/ docker-compose.yaml hack/ mdns-reflector.spec
  misc/ src/）。
- 根 `CMakeLists.txt` 与 `src/CMakeLists.txt` 均无 `enable_testing`/`add_test`/ctest 注册。
- `hack/` 只有 build-rpm.sh 打包脚本；`debian/` 只有打包元数据。

因此 build() 不跑上游套件，改为冒烟检查：`-h` 必须 rc=0 且输出含
"mDNS Reflector version"；无参数必须 rc!=0（真实 usage 错误路径）。

## test_package 说明（R34）

`test_package/test_mdns_reflector.py` 实际执行安装后的二进制，7 个断言：
1. `-h` 退出码为 0
2. 输出含 "mDNS Reflector version"
3. 输出含 "usage:"
4. 输出含 "IFNAME"
5. 无参数调用退出码非 0
6. 未知选项 `-Z` 退出码非 0
7. 可执行文件存在

不依赖网络接口/组播权限（真机 SELinux 下 bind 组播地址可能受限，故只测参数路径）。

## OHOS 适配点

- package() 内对产物做 OHOS ELF 自签名（llvm-objcopy 去 `.codesign` 段 +
  binary-sign-tool `-selfSign 1`，先例 ncdu/2.9.2、mdf2iso/0.3.1）；
  工具不存在时 warning 跳过（本机 Windows 无法签名，也不需要）。
- settings.os 仅允许 Linux/OHOS（R32 口径）。
- 无 conan requires；`commands.json`（R38，type=tool）已放在软件级目录。

## 本机（Windows）验证记录

- Python 语法：`py_compile` 通过（conanfile.py + test_package 两个配方 + 测试脚本）。
- YAML 结构：manifest.yaml / conandata.yml / test_package/MANIFEST.yml 解析通过。
- JSON 结构：commands.json 解析通过。
- SHA256 复核：归档重新下载校验一致。
- `git diff --check`：无空白错误。
- 本机无法 `conan create`（validate 限 Linux/OHOS；Windows 无 OHOS 工具链），
  属预期，留给真机/shadow CI。

## 下一步（真机 / shadow CI 命令）

真机 shadow CI 已于 2026-09-29 执行并通过（见下节）。

## 真机 shadow CI 结果记录（2026-09-29）

| 项 | r1 | r2 | r3 |
|---|---|---|---|
| run id（ohos-test-runs） | ...101938-18284 | ...102621-26473 | ...103345-38270 |
| 排队等待秒数 | 1 | 1 | 1 |
| exit code | 1 | 1 | **0** |
| L0 / L1 / L2 / L4 / L5 | blocked_by_KC | pass / fail / skip / skip / skip | **pass / pass / skip(-version) / pass / pass** |
| 上游测试 | 0（申报 0） | 0 | 0 |
| test_package | 未跑到 | 未跑到（source() 即失败） | **通过（含 L1e 反向验证）** |
| 报错原文 | `permission denied: git`（build_and_test.sh:164）+ `permission denied: bash`（KC 段） | `get() got an unexpected keyword argument '0.0.1'` | — |
| 根因 | 设备端 PATH 缺 `/data/service/hnp/bin`（bash/git 所在），与包无关 | conandata.yml 带版本嵌套层，与 `**conan_data["sources"]` 展开不匹配 | — |
| 解法 | 重跑前 `export PATH=/data/service/hnp/bin:$PATH` | conandata.yml 去掉 `"0.0.1":` 嵌套（对齐仓库惯例，如 ncdu/2.9.2） | — |

结论：Build Summary 1/1 success（100%）；L1e 破坏性负向测试确认 test_package
真实依赖包产物；L2 为 `skip: --version/--help failed`——上游 CLI 无 `--version`
选项（仅 `-h`，getopt 串 `"hdfp:n64l:"`），非阻塞。上游测试申报 0 项（清点证据
见上文 R51 节）。

设备端环境注意事项（给后续 shadow CI 复跑者，不含敏感信息）：
- runner 环境 PATH 必须包含 `/data/service/hnp/bin`（bash/git/zsh/clang 均在此），
  否则 CI 在 KC 段即 `permission denied` 失败。
- CI 会把 conandata.yml 源 URL 重写为镜像做预下载；设备无 curl 时预下载降级为
  conan 内建下载，可正常工作。
