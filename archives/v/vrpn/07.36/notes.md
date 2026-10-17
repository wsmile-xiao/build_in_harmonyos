# vrpn 07.36 适配笔记

## 编译环境
- 构建系统: cmake（根 `CMakeLists.txt` 44261 字节，位于归档顶层目录 `vrpn-07.36/`，非嵌套子目录）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（本仓 profile 编译器键名为 `cpp`，不是 `cxx`）
- 状态: built（2026-09-26 conan-verify 全绿 + finish W3 本地 CI 通过）

## 第 0 步：三条候选假设的一手读数（第 1 棒无落盘证据，本棒重做）

### 假设 ①「上游有 `.gitmodules` ⇒ submodule 分发形态」= **成立（证实）**

- 取证实物：`https://github.com/vrpn/vrpn/archive/refs/tags/v07.36.tar.gz`
  HTTP=200，SIZE=3088718，`url_effective=https://codeload.github.com/vrpn/vrpn/tar.gz/refs/tags/v07.36`
  sha256 `bed00ae060fc7c0cfdaa2fa01f6f2db4976d431971e8824b710eb63cfbba0df7`（三处独立实测同值，见「验证结果」）
- `tar tzf` 命中 `vrpn-07.36/.gitmodules`（1123 条目中唯一一枚），内容两条子模块：
  - `submodules/hidapi` → `https://github.com/vrpn/libusb-hidapi.git` @ branch `vrpn-utilized-head`
  - `submodules/jsoncpp` → `https://github.com/vrpn/jsoncpp.git`
- **子模块目录在该 tag 归档里是空的**：tar 只列 `submodules/hidapi/`、`submodules/jsoncpp/` 两枚目录条目、无子文件；解包后 `ls -la submodules/hidapi submodules/jsoncpp` 亦为空目录。⇒ GitHub codeload 的 tag 归档不含 gitlink 内容。

### 假设 ②「处置方向：make-dist 资产优于 tag 归档，存在 `vrpn_07.35.zip`/`vrpn_07.34.zip`」= **对 07.35/07.34 成立、对目标版本 07.36 不成立**

`GET /repos/vrpn/vrpn/releases?per_page=100` 全量 4 条 Release（逐条打印 `tag_name` / `name` / `assets[].name` / `size`）：

| tag | release name | assets |
|---|---|---|
| `v07.36` | `Version 07.36` | **`[]` 零资产** |
| `version_07.35` | `Version 07.35 with submodules expanded` | `vrpn_07.35.zip` 32848420 |
| `version_07.34` | `Version 07.34 with submodules expanded` | `vrpn_07.34.zip` 32700105 |
| `v07.33` | `version_07_33_with_submodules_updated` | `vrpn_07_33.zip` 19445878 |

另探 `releases/tags/version_07.36` → **HTTP 404**（该 tag 无 Release 对象）。
⇒ 声称的 07.35/07.34 两枚 make-dist 资产**真实存在**，但**任务目标版本 07.36 没有任何"submodules expanded"资产**；换用 07.35 资产会破坏"任务/归档/分支/配方四处版本串一致"硬规则，不是本棒可做的选择。

### 假设 ③「子设备服务全可关」= **机制层成立，逐项开关数已清点**

根 `CMakeLists.txt` 的服务开关由 `option_requires(<OPT> ...)` 承载（该宏语义 = 需求不满足则**自动 OFF**，非 FATAL_ERROR）：共 **20 条** `option_requires`（行号 338/345/351/369/382/398/413/437/468/481/497/518/531/548/564/579/606/652/656/668，覆盖 PYTHON 系列、JAVA、MPI、MODBUS、LIBUSB_1_0、HID、HDAPI、GHOST、PHANTOM_SERVER、I2CDEV、WIIUSE、JSONNET、LIBNIFALCON、DIRECTINPUT、XINPUT、DIRECTSHOW、DIRECTSHOW_VIDEO_SERVER、GPM_MOUSE）+ **9 条**裸 `option(VRPN_USE_*/VRPN_INCLUDE_*/VRPN_BUILD_*)`（行号 813/831/863/899/902/903/906/909/948/950/951）。
`find_package` 面（根 CMakeLists 去重）：Adrienne ColibriApi DirectShow DirectX GHOST GPM HIDAPI I2CDEV InterSense JNI Java JsonCpp LibFreespace LibNifalcon Libusb1 MPI Modbus NIDAQmx OpenHaptics Perl PerlModules Python SWIG ThalmicLabsMyo Threads ViewPoint WiiUse —— 除 `Threads` 外全部走 `option_requires`/平台分支门。

### 子模块缺失时 CMake 的实测降级行为（决定"要不要手搬 submodule"的关键读数）

`submodules/jsoncpp.cmake` 原文：

```cmake
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/jsoncpp/include/json/json.h")
	set(LOCAL_JSONCPP_SUBMODULE_RETRIEVED TRUE)
else()
	set(LOCAL_JSONCPP_SUBMODULE_RETRIEVED FALSE)
	if(NOT SUBPROJECT)
		message(STATUS
			"Local JSONCPP submodule not found. To download with Git, run git submodule update --init")
	endif()
endif()
option_requires(VRPN_USE_LOCAL_JSONCPP
	"Build with JSONCPP code from within VRPN source directory"
	LOCAL_JSONCPP_SUBMODULE_RETRIEVED)
```

`submodules/hidapi.cmake` 同构（`LOCAL_HIDAPI_SUBMODULE_RETRIEVED FALSE` + `option_requires(VRPN_USE_LOCAL_HIDAPI ...)`，仅 ANDROID 分支才要求外部 HIDAPI 源树）。
⇒ **子模块为空时 `add_subdirectory(submodules)`（根 CMakeLists 第 246 行）不报错，`VRPN_USE_LOCAL_*` 自动关闭**，不需要把子模块源码搬进归档即可完成 configure。是否因此丢功能属产品判断，已上报主理裁。

## 编译步骤

本棒实际命令链见文末「本棒执行明细」：preflight rc=0 → recipe-search rc=0 → init-build rc=0 → build Step[1-5] 绿 → conan-verify 第 5 轮全绿 → finish rc=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 第 1 棒 0 提交、探索结论未落盘 | 服务连接中断 | 本棒按第 0 步口径重做全部读数并逐条落盘（本文件 + knowledge-candidate-ledger.md） |

## 依赖版本

- 无强制外部依赖：preflight rc=0「无依赖需要检查」。
- 可选依赖按第 0 步读数自动降级：jsoncpp/hidapi 子模块为空 ⇒ VRPN_USE_LOCAL_JSONCPP/HIDAPI=OFF（主理已裁决接受）。
- Threads 为 find_package 面中唯一非 option_requires 门，系统提供。
- 工具链：clang 15.0.4 + cmake 4.1.2（hnp）+ GNU Make 4.4.1 + conan 2.29.1 + profile ohos-aarch64。

## 验证结果

```bash
# 取源哈希三处独立实测（命令原样）
# A) 鸿蒙 B 机
curl -sSL -w "HTTP=%{http_code} SIZE=%{size_download} URL=%{url_effective}\n" \
  -o official-v07.36.tar.gz https://github.com/vrpn/vrpn/archive/refs/tags/v07.36.tar.gz
# HTTP=200 SIZE=3088718 URL=https://codeload.github.com/vrpn/vrpn/tar.gz/refs/tags/v07.36
sha256sum official-v07.36.tar.gz
# bed00ae060fc7c0cfdaa2fa01f6f2db4976d431971e8824b710eb63cfbba0df7  official-v07.36.tar.gz
# B) Windows 侧 Git Bash 独立下载同址：HTTP=200 SIZE=3088718，sha256 同值
# C) 第 1 棒留下的 vrpn-07.36.tar.gz sha256 同值 ⇒ 三处一致，归档哈希可复现

# 归档结构与开关清点
tar tzf vrpn-07.36.tar.gz | wc -l                # 1123
tar tzf vrpn-07.36.tar.gz | grep gitmodules      # vrpn-07.36/.gitmodules
ls -la src/vrpn-07.36/submodules/hidapi src/vrpn-07.36/submodules/jsoncpp   # 均为空目录
grep -c "^option(VRPN_USE" CMakeLists.txt        # 9
grep -n "option_requires" CMakeLists.txt         # 20 处
grep -ho "find_package([A-Za-z0-9_]*" CMakeLists.txt | sort -u
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| archives/v/vrpn/07.36/conanfile.py | 配方 | 六库 package_info + BUILD_TESTING=OFF |
| archives/v/vrpn/07.36/patches/0001-CMakeLists.txt.patch | +1/-1 | atmellib 门控 if(UNIX)→NOT WIN32 |
| 包 lib/ 6 库 | libvrpn/libvrpnserver/libquat/libgpsnmea/libvrpn_atmel/libvrpn_timecode_generator (.a) | 静态（R26 默认 shared=False） |
| 包 bin/ 8 工具 | vrpn_server 等 | commands.json 已声明（R38） |

## 注意事项

- **tag 归档不含子模块内容，且 07.36 无 make-dist 资产**（本文件第 0 步）：hidapi/jsoncpp 两处子模块在 configure 阶段自动降级关闭。若产品要求保留 HIDAPI/JSONCPP 通道，需主理裁决（换版本 = 违规；手搬子模块源码 = 范围扩大）。
- 版本串四处一致取 `07.36`，不归一化为 `7.36`；上游同时存在 `v07.36` 与 `version_07.36` 两枚 tag，本归档只认 `v07.36`。
- 上游 tag 归档目录名为 `vrpn-07.36/`（codeload 生成），配方 `source()`/`exports_sources` 需按该前缀处理。
---

**编译结束**: 2026-09-26 02:54
**最终状态**: built

## 本棒（主理-60）执行明细（2026-09-26）

### 编译步骤（实际命令，均经 build-slot.sh --kind long --mem 8000 包装、gate.sh 过闸）

环境（SSH 非登录 shell 每次显式带）：

    export CONAN_HOME=~/tmp/ch/home-vrpn SSL_CERT_FILE=~/usr/local/ssl/cert.pem
    export PATH=~/tmp/uc2/vrpn/shim:/data/service/hnp/autoconf.org/autoconf_2.72/bin:/data/service/hnp/pkg-config.org/pkg-config_0.29.2/bin:/data/service/hnp/perl.org/perl_5.42.0/bin:~/usr/local/bin:~/.local/bin:/storage/Users/currentUser/.local/bin:/storage/Users/currentUser/.harmonybrew/bin:/storage/Users/currentUser/.harmonybrew/sbin:/usr/local/bin:/data/app/bin:/data/service/hnp/bin:/usr/bin:/vendor/bin
    export PERL5LIB=~/usr/local/share/automake-1.16

1. bash ci/scripts/preflight_check.sh vrpn/07.36 —— rc=0（无依赖需检查）
2. python3 scripts/ohc-run.py recipe-search vrpn —— rc=0（无相似配方，走模板线）
3. python3 scripts/ohc-run.py init-build vrpn 07.36 --url=https://github.com/vrpn/vrpn/archive/refs/tags/v07.36.tar.gz —— rc=0（需下述 shim 环境，见问题 #2）
4. python3 scripts/ohc-run.py build vrpn 07.36 —— Step[1-5] 绿（探索构建全部目标 Built，含 libvrpn_atmel.a 与 vrpn_server 链接，build.log 138-145 行）；Step[6/14] R7 弹窗检查挂死（问题 #8）
5. python3 scripts/ohc-run.py conan-verify vrpn 07.36 —— 第 5 轮全绿（G0-G4 + L2/L4/L5；前四轮失败见问题 #3-#6）
6. python3 scripts/ohc-run.py finish vrpn 07.36 built —— rc=0（问题 #7 修复后；W3 本地 CI 通过，manifest → built）

### 遇到的问题与解决方案（续，#2-#8）

2. init-build 崩 NameError（check_env.py:33 假红）：真因 automake/aclocal 的 shebang 指向不存在的 ~/usr/local/bin/perl（ENOENT），且 autoconf/pkg-config 不在默认 PATH。不改框架件/不动 ~/usr/local：~/tmp/uc2/vrpn/shim/ 放 automake、aclocal 包装器用 hnp perl5.42 显式执行 + PATH 前置 hnp 的 autoconf/pkg-config + PERL5LIB 指 automake-1.16 share。
3. G2 首败「ld.lld: unable to find library -lvrpn_atmel」：CMake 原生探测 CMAKE_SYSTEM_NAME=HarmonyOS（uname -s），无对应 Platform 模块 ⇒ UNIX 变量为 FALSE（探针实测 UNIX= 空，Platform/ 下只有 OHOS.cmake 无 HarmonyOS.cmake）⇒ atmellib 被 if(UNIX) 门掉，而 server 侧按 NOT WIN32 引用 vrpn_atmel。E092 机制细化。修复：补丁 0001 将门控改为 if(NOT WIN32)（无平台宏，过 PF5）。
4. G2 二败「Library quatserver not found in package」：package_info 多声明（包内实装无 quatserver，上游未安装），且漏 vrpn_timecode_generator。修复：按包内 lib/ 实测 ls 对齐为六库。
5. G2 三败「fatal error: new file not found」：test_package 原为 test.c（C 编译），VRPN 公共头是 C++ 头（vrpn_Shared.h 无条件 include new）。修复：test.c → test.cpp + project(test_vrpn CXX)。
6. G2 四败「undeclared identifier vrpn_Connection_Destroy」：该 API 在 v07.36 不存在。按包内头文件（vrpn_Connection.h:771）改用公开 API conn->removeReference()。
7. finish W3 首败「Patch file does not exist: 0001-atmellib-not-win32.patch」：finish Step[1/10] refresh-patch --auto 重新生成补丁（0001-CMakeLists.txt.patch）并把旧名补丁挪进 patches/.patch-backup-*，conandata 仍指旧名。修复：conandata patch_file 对齐 refresh-patch 产物。
8. build 链 R7 安全弹窗步骤挂死（02:12:46 起 6 分钟无进展）：弹窗检查逐个跑 bin/* --version，bdbox_client（上游 vrpn 自带示例，client_src/bdbox_client.C）不认 --version 且读 stdin，5s 超时异常致检查线程死亡、整链挂起。处置：按 R11 手动模式接管，终止该驱动后手动续 conan-verify + finish；G2 复验与 W3 本地 CI 均独立通过，结果等价。

### 验证结果锚点（2026-09-26）

- conan-verify 终局全绿（G0-G4 + L2/L4/L5），W3 本地 CI 通过：reports/w3-local-ci.log（L0/L1/L2/L4/L5 = pass，Build Summary Success 1 Failed 0）。
- test_package ctest 实测：1/1 Passed（test_vrpn 1.03s，「100% tests passed, 0 tests failed out of 1」，.ci_logs/conan_build_vrpn_07.36.log 719-724 行）。
- 包产物 lib/（ls 实测）：libvrpn.a、libvrpnserver.a、libquat.a、libgpsnmea.a、libvrpn_atmel.a、libvrpn_timecode_generator.a；bin/ 8 个工具（vrpn_server 等）。
- L2 smoke：run_auxiliary_logger/vrpn_log_devices/vrpn_server --version OK；其余 5 个示例程序不认 --version 探针（L2 总评 pass）。

### 上游测试三步法申报（R51）

- 静态清点：上游 client_src TEST_SOURCES 等测试程序在探索构建（全默认）中可见 26 条「Built target test_*」日志行（含并行重复，去重 18 个唯一测试目标；grep -c 实测，W60-1 整改：原记 32 条系执行棒误记，经复核实为 26）；包构建（BUILD_TESTING=OFF）不含这些测试程序。
- 实测：test_package 内 ctest 1/1 通过（见上）；L2 smoke 8 样本 3 OK / 5 不适用（--version 不支持）。
- 跳过：包内上游测试套件未逐项运行（BUILD_TESTING=OFF 属配方裁剪，非运行时跳过；依据 client_src/CMakeLists.txt 的 if(BUILD_TESTING) 门与探索构建对比）。
- 失败：0（ctest 0 failed）。

### 对话记录

- 第 1 棒（主理-45）：第 0 步三假设读数落盘、骨架与配方初稿（服务中断前抢救提交）。
- 第 2 棒（主理-60 子代理）：构建链到绿（本文件「执行明细」），提交 cd9542fac3 / 6f3bf54434 / e28f892dc4 / 7e0888e3b6 / 4c9370e15a / 本笔。



## 路径 B 声明（3+2）

- 适配路径：路径 A（标准 Conan 配方流程）＋ 知识库扩展（B 判定=create）
- 使用知识库：E092（CMake 不识别 HarmonyOS 平台，configure 期 + toolchain 方案）、E532（平台三分支 else 兜底 FATAL + HarmonyOS 判据方案）——同根因对照条目；症状与解法差异论证见 knowledge/drafts/DRAFT-11759-vrpn-07.36-cmake-unix-var-false-gated-subdir-link-fail.md 与本 notes「第 0 步」及问题表 #4
- 知识库扩展：knowledge/drafts/DRAFT-11759-vrpn-07.36-cmake-unix-var-false-gated-subdir-link-fail.md/.kv——HarmonyOS 无 CMake 平台模块致 UNIX 变量 FALSE，if(UNIX) 门控子目录被静默跳过、链接期缺库；修法=门控宏对齐 if(NOT WIN32)（零平台宏）。draft-review 质量预检 3/3 ✅
- 关联 Issue：#3436（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3436）
