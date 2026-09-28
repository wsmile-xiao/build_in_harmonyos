# libmicrodns 0.2.0 适配笔记

## 概览

- 上游仓库: https://github.com/videolabs/libmicrodns （VideoLAN，VLC 的 mDNS/DNS-SD 服务发现组件）
- 上游版本/tag: 0.2.0（与 Conan 包版本一致，无 R37 递增）
- 许可证: LGPL-2.1-or-later
- 语言/构建系统: C99 / meson (>= 0.50)
- 语言预检 (R47): C，属于 c↔cpp 兼容族，conan 流程通吃
- Conan 包类型: library（纯库，无 bin/ 产物，无需 commands.json (R38)）

## W0 依赖结论

```text
依赖数量: 0（Conan 依赖）
已满足依赖: 无需（POSIX/OHOS 目标零外部依赖；仅 Windows 目标需系统库 ws2_32/iphlpapi，由 meson 与 package_info 各自声明）
缺失依赖: 无
是否需要拆分依赖适配: 否
阻塞点: 无
下一步: 真机 shadow CI
```

制品仓探测（R35 口径，公开 API `v2/conans/search?q=libmicrodns/*`，对照组 zlib 正常返回）:
libmicrodns 在制品仓无任何版本 → 首次适配，保持 0.2.0。

## 历史归档核验 (W0b)

本目录已有 2026-05-28 的手工探索归档（notes.md / manifest.yaml / hints/env.sh）：
设备上手动 meson 构建，1/1 上游测试通过，当时状态标记 published —— 但归档中**没有
conanfile.py / conandata.yml / test_package**（manifest 连 sha256 都是空的），
即从未以 Conan 配方形态进入 CI/制品仓。本次适配补齐 Conan 交付物，历史结论全部保留在
本文件末尾。

历史踩坑比对（W0b 第 2 项）:

| 历史 notes 教训 | 本次配方处理 | 状态 |
|---|---|---|
| meson 找不到编译器，需 CC/CXX 完整路径 | profile `tools.build:compiler_executables` 提供完整路径 | 已覆盖 |
| llvm-ar 不在默认检测路径 | `_inject_meson_tools()` 向 machine file 注入 ar/ranlib（cairomm 1.16.2 同款） | 已覆盖 |
| 干净构建可行（手动 G0 验证） | 本机用 OHOS SDK 交叉工具链复现干净构建 | 已复现 |

## 源码/构建系统分析 (W1)

- 源码归档: 官方 tag archive `refs/tags/0.2.0`（tar.gz，含完整 tests/），SHA256 见 manifest.yaml
- 产物: `library('microdns', ...)` → libmicrodns.a/.so（soname libmicrodns.so.1）
- 上游 meson.build 的 host_system 仅特判 `'windows'`；适配版 conan 将 os=OHOS 映射为
  system `'harmonyos'`，POSIX 能力探测（HAVE_INET_NTOP/HAVE_POLL/HAVE_STRUCT_POLLFD/
  HAVE_GETIFADDRS/HAVE_IFADDRS_H）由编译器探测自动判定——E090/E355 的 host_system
  误判问题对本库不适用，无需补丁
- 上游测试: tests/unittests.c 单个 meson test 可执行文件（纯 assert，无外部测试框架），
  历史真机实测 1/1 通过（0.04s）
- examples（listen/announce）非交付物，配方中显式 disabled；fuzzing 保持默认关闭

## Conan 配方设计 (W2/W3)

- `conanfile.py`: meson 模板；`tests=enabled`（上游测试进 build()，cross_building()
  时自动跳过）；`examples=disabled`；OHOS 分支复用 cairomm 1.16.2 验证过的
  `-fuse-ld=ld.lld` + machine file ar/ranlib 注入（lld 通用驱动依赖 libxml2.so.16，
  设备上不在动态链接器搜索路径，E296/cairomm 经验）
- `conandata.yml`: 官方 tag archive URL + 本地实测 SHA256；无补丁
- `test_package/`: 消费者程序以 `#include <microdns/microdns.h>` + `<microdns/rr.h>`
  使用安装后的公开 API——8 项检查（mdns_strerror 未知码/MDNS_STDERR/零长度缓冲、
  MDNS_PORT/MDNS_ADDR_IPV4/MDNS_ADDR_IPV6 常量、rr_type RFC 值、rr_entry 链构建 +
  mdns_entries_print 遍历），无网络、确定性强、断言独立于上游 unittest
- 默认静态链接（shared=False），消费者二进制自包含，可在 OHOS CI（设备原生 worker）
  上直接执行，不受 musl 动态链接器搜索路径限制（cairomm notes 描述的平台约束）

## 本机验证 (W4)

环境: Windows 11 x64 + DevEco Studio OHOS SDK（native/llvm clang 15.0.4 + sysroot）
+ venv 安装的 OHOS 适配版 conan 2.29.1 / meson 1.12.1 / ninja。验证用 profile 为
本机临时文件，不在提交范围内。

| # | 验证项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 配方/测试源码语法 | `python -m py_compile conanfile.py test_package/conanfile.py` | 通过 |
| 2 | conandata/MANIFEST/manifest YAML 解析 | python yaml.safe_load | 通过 |
| 3 | 源码 SHA256 复核 | sha256sum 下载归档 | 与 conandata 一致 |
| 4 | 配方 generate() 输出 | `conan create ... -pr:h/-pr:b`（Windows 宿主→OHOS 交叉） | 生成 conan_meson_cross.ini 正确（host=harmonyos, ar/c_ld/--target/--sysroot 齐备）；settings/options 识别正确 |
| 5 | OHOS 目标完整编译 | meson setup + ninja（用第 4 项生成的同款 cross file + POSIX prefix） | libmicrodns.a + tests/unittest 交叉编译成功；仅上游 1 条 -Wcast-align 警告 |
| 6 | 安装布局 | meson install --destdir | lib/libmicrodns.a、include/microdns/{microdns.h,rr.h}、lib/pkgconfig/microdns.pc，无 bin/ |
| 7 | 消费者编译链接 | target clang 编译 test_libmicrodns.c -lmicrodns（静态） | aarch64 OHOS ELF 生成；mdns_strerror/mdns_entries_print 符号解析 |

本机 conan create 在 meson setup 一步被上游 conan 行为挡住：Meson helper 硬编码
`--prefix=abspath('/')`，Windows 宿主上为 `C:/`，POSIX 目标的 meson 拒绝
（ERROR: prefix value 'C:/' must be an absolute path）。这是 conan Windows 宿主的
已知行为（conan-io/conan#14213 一族），配方无法覆盖；OHOS 设备原生 CI 上 prefix=`/`
不受影响（cairomm 1.16.2 已在同管线验证 meson+install 全流程）。第 4-7 项即以
conan 自身生成的 machine file 等价复现了 build()/package() 的关键路径。

本机环境修复记录（不属于 PR 内容）: 本机 `~/.conan2/settings.yml` 为旧版缓存、缺
OHOS 枚举，按 ci/conan/setup.sh §1b 同款处理删除再生（已留备份）。

## 未执行/待执行项（如实申报）

- ~~test_package 消费者二进制执行与上游 meson test 运行~~ → **已由真机 shadow CI 完成（见下）**
- 竞赛 CI（PR 触发）: 待分支 push 后运行

## W5 真机 shadow CI 结果（2026-09-27）

HarmonyOS PC 真机（aarch64 原生 worker，单包全局锁排队）shadow CI **通过，exit code 0**：

```text
G0_RESULT=pass
G0e_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass: empty
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
  L1a: test_package was executed by conan create
  L1b: test execution evidence found in log
  L1c: upstream official tests executed in build phase
L2_RESULT=skip: no bin/ dir          # 纯库正常现象
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content
conan create: 1/1 success (100%)
```

- 上游测试: `meson test -v` 原生执行，**1/1 microdns:unittest OK（0.03s）**，与
  2026-05-28 历史手工记录（1/1, 0.04s）一致
- test_package 消费者测试: **8/8 断言通过**（含 mdns_strerror 三态、协议常量、
  rr_entry 链 + mdns_entries_print 真实 JSON 输出验证）
- 配方在设备原生环境的自动行为全部符合设计：os=OHOS → meson native（`--prefix=/`），
  `_inject_meson_tools` 注入 ar/ranlib，`meson.test()` 因非交叉而执行
- 共 6 轮到达通过：r1 隔离 job repo 复制不完整（缺 infra 目录）→ r2 设备登录 PATH
  缺 bash/git（新版门禁脚本需要）→ r3-r5 暴露 repo-source 的 git 索引中残留的
  非白名单文件（G0e 按 `git ls-files` 检查索引而非工作区）→ r6 清理后全绿。
  全部为 shadow 环境问题，配方零修改。

## 下一步: 真机 shadow CI 命令（设备地址等敏感信息见避坑指南 §7，不写入本文件）

```sh
# 1) 连通性检查（先轻后重）
ssh -i ~/.ssh/ohos_pc_codex_ed25519 -p 2222 -o StrictHostKeyChecking=accept-new \
  -o IdentitiesOnly=yes currentUser@<device-ip> "echo ok"

# 2) 创建隔离 job（单包排队; 若设备无 git, --repo-source 指向设备上已有 repo）
job="libmicrodns-0.2.0-$(date +%Y%m%d%H%M%S)"
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex --job "$job" \
  --package archives/l/libmicrodns/0.2.0 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"

# 3) 传输包目录（scp 或 base64, 禁止文本管道 tar）后核对文件清单
find archives/l/libmicrodns/0.2.0 -maxdepth 3 -type f | sort

# 4) 执行 runner 并记录 L0-L5 / 上游测试 / test_package 结果
sh "$HOME/ohos-users/codex/$job/run-conan-heavy.sh"
```

预期: L0/L1/L4/L5 pass，L2 skip（无 bin/ 目录，纯库正常现象，对照 xmodem）；
上游测试 1/1；test_package 8/8 断言。

---

## 历史归档（2026-05-28 手工探索，结论保留）

### 编译环境
- 构建系统: meson
- 编译日期: 2026-05-28
- 编译器: clang/clang++ (15.0.4)
- 链接器: llvm-ar
- 状态: built

### 编译步骤

1. 下载源码: https://github.com/videolabs/libmicrodns/archive/refs/tags/0.2.0.tar.gz
2. 设置环境变量:
   ```bash
   export CC=/data/service/hnp/bin/clang
   export CXX=/data/service/hnp/bin/clang++
   export AR=/storage/Users/currentUser/usr/local/bin/llvm-ar
   ```
3. 配置 meson: `meson setup builddir --prefix=/storage/Users/currentUser/usr/local`
4. 编译: `cd builddir && ninja -j2`
5. 安装到 staging: `meson install -C builddir --destdir=$TEST_PREFIX`
6. 测试: `meson test` —— 1/1 通过

### 历史问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到编译器 | meson 检测编译器用简单命令名，PATH 中 clang 不可直接执行 | 完整路径环境变量 CC/CXX/AR |
| 2 | meson 找不到链接器 ar | llvm-ar 不在默认检测路径 | 同上，设置 AR |

### 历史验证结果

```text
1/1 microdns:unittest OK              0.04s
Ok: 1  Fail: 0
手动 G0 干净构建验证: 配置成功
```

### 历史交付物

libmicrodns.so.1.0.0（及 .so.1/.so 链接）、microdns.pc、microdns.h、rr.h

---

**本次适配**: 2026-09-27（Conan 配方 + test_package + 本机交叉验证 + 真机 shadow CI 通过）
**当前状态**: built（shadow CI 全绿；待 push → PR → 竞赛 CI → release 发布）
