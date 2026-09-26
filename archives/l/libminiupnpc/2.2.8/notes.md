# miniupnpc 2.2.8 适配笔记

## 编译环境

- 构建系统: direct-cc（复用 2.3.11 验证过的直调编译路线）
- 编译日期: 2026-09-23
- 编译器: clang/clang++（OHOS aarch64 profile）
- 状态: built
- 目标平台: HarmonyOS aarch64 (OHOS 6.0, clang 15, libc++)

## 版本与源码说明

- 上游 monorepo github.com/miniupnp/miniupnp，tag `miniupnpc_2_2_8`（客户端线 tag，注意 tag 名带下划线格式，git ls-remote 确认：b55145ec095652289a59c33603f3abafee898273）。
- 与 2.3.11 用的 daemon 线 tag（miniupnpd_2_3_11，project VERSION 仍是 2.3.3）不同，2.2.8 的 tag 就是客户端线本线：`miniupnpc/VERSION` = 2.2.8，`CMakeLists.txt` `project(VERSION 2.2.8)`，`include/miniupnpc.h` `#define MINIUPNPC_VERSION "2.2.8"`，包版本与上游版本完全一致，无需版本错位说明。
- 源码取 codeload 归档 `.../tar.gz/refs/tags/miniupnpc_2_2_8`，sha256 `3d0d49f761f09c1321ceb663d1b008825361d7bd242640c60ae467e82642502a`，`strip_root` 后顶层为仓库根（含 miniupnpc/miniupnpd/minissdpd 等子目录），配方直接取 `miniupnpc/` 子目录。
- codeload URL 无文件扩展名，`source()` 须传 `filename` 供 Conan 解包（沿用 zfp/2.3.11 经验）。
- 包名对齐仓内已用名 `miniupnpc`（2.3.2/2.3.3/2.3.3.1/2.3.11 同名同路径 m/miniupnpc），制品仓 miniupnpc/2.3.3+2.3.11 为他人新线，本 2.2.8 为旧线适配。

## 编译步骤（direct-cc 路线）

仓库自己的 2.3.11 适配已证明 CMake project() 在 OHOS CI 上必然红（"The C compiler identification is unknown"，HarmonyOS 默认映射与 CMAKE_SYSTEM_NAME=Linux 覆写两条路线都试过），故 2.2.8 直接沿用 direct-cc：

```text
build():
  1. 可写 TMPDIR 保障（/tmp 只读，HMBS 注入 TMPDIR 优先）
  2. cc/ar 从 Conan conf tools.build:compiler_executables 取（R33），不裸用 ${CC}
  3. C 编译器冒烟（真 stderr，防 CMake 式静默失败）
  4. 生成 miniupnpcstrings.h（OS_STRING="Linux"，MINIUPNPC_VERSION_STRING="2.2.8"，
     UPNP_VERSION 块齐——minisoap.c 的 User-Agent snprintf 需要它）
  5. 14 个纯 C TU（CMakeLists MINIUPNPC_SOURCES 同表）-std=c99 -fPIC -Wall -O2
     + 上游非 Win32 defines（MINIUPNPC_SET_SOCKET_TIMEOUT/MINIUPNPC_GET_SRC_ADDR/
     _BSD_SOURCE/_DEFAULT_SOURCE/_XOPEN_SOURCE=600）
  6. llvm-ar rcs 归档 libminiupnpc.a（shared=True 时另产 .so）
  7. 上游 7 项测试真跑（见下节）
```

## 上游测试审计

- 源码 `miniupnpc/CMakeLists.txt` 中 `UPNPC_BUILD_TESTS` 段注册 7 项 CTest（与 2.3.x 线完全同构）：
  - `validateminixml`（`minixmlvalid` 二进制）
  - `validateminiwget`（`testminiwget.sh` + `minihttptestserver`，需 `TESTSERVER`/`TESTMINIWGET` 环境，脚本用 `mktemp -d`，依赖 HMBS 注入的 writable TMPDIR）
  - `validateupnpreplyparse`（`testupnpreplyparse.sh`，遍历 `testreplyparse/*.xml`）
  - `validateportlistingparse`
  - `validateigddescparse1`（`new_LiveBox_desc.xml`）
  - `validateigddescparse2`（`linksys_WAG200G_desc.xml`）
  - `validateaddr_is_reserved`
- 配方在 `build()` 内按 CMakeLists.txt 的源码清单直编这 7 个 harness 并全部真跑（非 CTest 包装，等效覆盖），结果写入 `build_folder/upstream_test_result.json`，`package()` 拷贝至 `package/res/` 供 `test_package` 回显（防 conan cache 跳过 build() 时标记丢失）。
- `testminiwget.sh` 在无 `ip`/`ifconfig` 时回退 `localhost`，HarmonyOS 真机可跑；`mktemp` 依赖可写 TMPDIR（配方已保障）。
- `src/testupnpreplyparse.c` 的 `FILE * f;` 未初始化 UB 在 2.2.8 同样存在（同 2.3.11 真机日志：栈槽非零时 DeletePortMapping.namevalue 被"unrecognized argument"拒绝、validateupnpreplyparse rc=1）——配方内零初始化该局部变量，仅动测试壳、不动库本体，7 用例数与覆盖不变。
- N 口径：**上游构建系统注册的测试目标数 N=7**（CMakeLists add_test 计数），实测 7/7 全过。UPnP 真设备发现类（upnpc 样例的 GetValidIGD 实网调用）不在注册测试集内，test_package 用无设备环境下的 API 冒烟（upnpDiscover 超时返回 + freeUPNPDevlist）作消费者测试补充。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 在 OHOS 上红 | "The C compiler identification is unknown"（无 Platform/HarmonyOS 模块） | 弃 CMake，direct-cc 直调 profile clang（2.3.11/critnib/ddate 先例） |
| 2 | codeload URL 无扩展名导致 Conan 解包失败 | `get()` 无法推断格式 | `source()` 传 `filename="miniupnp-miniupnpc_2_2_8.tar.gz"`（zfp/2.3.11 经验） |
| 3 | testupnpreplyparse 真机偶发 FAILED | `FILE * f` 未初始化 UB，栈槽非零时 namevalue 文件走错分支 | 配方内 `FILE * f = NULL;` 零初始化（仅测试壳，2.3.11 验证过的修法） |
| 4 | /tmp 只读，mktemp 系测试脚本失败 | HMBS 平台 /tmp 只读 | 配方 `_ensure_writable_tmp()`：HMBS 注入 TMPDIR 优先，兜底 build_folder/tmp |

## 与 2.3.11 配方的关系

同构复用：源清单/测试清单/defines/安装布局完全一致（上游两版本 CMakeLists 同构），仅三处差异——
1. `conandata.yml` URL/sha256 换 2.2.8 tag；
2. `_UPSTREAM_PROJECT_VERSION = "2.2.8"`（miniupnpcstrings.h 里的版本串）；
3. 去掉 `build_samples` option（2.2.8 不构建样例，UPNPC_BUILD_SAMPLE 对应关闭）。
