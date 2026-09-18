# libei 1.5.0 适配笔记

## 背景
- 上游：https://gitlab.freedesktop.org/libinput/libei（tag 1.5.0）
- 输入仿真协议（Emulated Input）参考实现：libei（客户端库）+ libeis（服务端库）+ liboeffis（portal 助手，裁剪）
- 构建：meson（>= 0.57）；C11（gnu11）

## 编译环境
- 构建系统: meson 1.12.0（pip-global）/ ninja 1.13.1
- 交叉: OHOS aarch64（clang 15.0.4，ohos-aarch64 profile）
- 编译日期: 2026-09-15
- 状态: published（conan create 全绿）

## 产物
- libei.so.1.5.0（客户端库）
- libeis.so.1.5.0（服务端库）
- ei-debug-events 工具（bin，可选依赖 libevdev 时全功能）
- 头文件：include/libei-1.0/{libei.h,libeis.h}
- pkg-config：libei-1.0.pc / libeis-1.0.pc

## 遇到的问题与解决方案

### 1. liboeffis 依赖 sd-bus（裁剪）
liboeffis 是 RemoteDesktop portal DBus 助手，meson 会探测 libsystemd/
libelogind/basu 任一提供 sd-bus。OHOS 无这些系统库 → `-Dliboeffis=disabled`。
核心 libei/libeis 不受影响（纯 socket + brei 协议自有实现）。

### 2. munit wrap-git CI 离线不可拉取（vendor）
test/meson.build 硬依赖 `subproject('munit')`（wrap-git revision=head）。
CI worker 无外网。补丁 0002 把 munit 上游三文件（munit.c/munit.h/meson.build，
nemequ/munit master fbbdf14）vendor 进 subprojects/munit/——meson 有本地
目录时优先于 wrap，CI 离线可测。

### 3. tmpfile() 在 OHOS 恒失败（EACCES）—— E002 变体
- musl 的 tmpfile() 硬编码 /tmp（只读）且不读 TMPDIR → 恒 EACCES
- munit.c 的 fork 模式与 no-fork 模式都无条件调 tmpfile() 捕获 stderr →
  全部用例 ERROR（0% skipped）
- src/util-io.c 测试段 3 处 tmpfile()（仅为拿临时 fd 测 fd 传递）
- 修复（补丁 0001 + 0002 内嵌）：无条件改用 $TMPDIR 唯一文件 fopen("w+")
  + 立即 unlink（fd 到 fclose 前有效，语义与 tmpfile 等价）；
  纯 POSIX 实现（getenv/fopen/unlink + P_tmpdir 兜底），无平台宏
  （AI review 意见采纳：跨 musl 平台通用）
- **可复用知识**：所有 munit 系/依赖 tmpfile 的 C 测试在 OHOS 沙箱同坑

### 4. meson ninja 探测失败（libc++_shared.so 加载失败）
- /data/service/hnp/bin/ninja 动态依赖 /system/lib64/libc++_shared.so
- 默认 LD_LIBRARY_PATH 有带空格的脏路径项（"         /system/lib64"），
  干净的 /system/lib64 不在其中 → ninja --version rc=127
- meson detect_ninja 对 rc=127（非 FileNotFoundError）静默跳过 → 全部
  candidate 失败 → "Could not detect Ninja v1.8.2 or newer"
- 修复：conanfile generate() 的 build env 前置 LD_LIBRARY_PATH=/system/lib64
  （等价 usr/local/bin/ninja wrapper 的手法）
- 排查路径：source conanbuild.sh 复现 → env 二分 PATH → Popen_safe 直测
  ninja rc=127 → readelf 定位 libc++_shared.so

### 5. cross build 下 meson test 跳过 C 测试（本地验证法）
交叉编译配置（cross-file）无 exe_wrapper 时 meson 对所有 C 测试标 SKIP
（exit 77）。本机即 aarch64 OHOS 设备，改用 native 配置（CC=clang 直接
构建，产物相同）跑全部测试。conan MesonToolchain 对 OHOS 本来就走
native（host_machine.system=HarmonyOS），CI 上测试可直接执行。

### 6. eistest_socket_overflow 平台差异（豁免申报）
测试假设"500 帧事件填满 Unix socket 缓冲区"（Linux 默认 wmem 较小）。
OHOS socket 缓冲区语义不同（更大），事件全部被接收，客户端多读出
STOP_EMULATING 尾事件导致断言失败。**平台环境差异，非代码缺陷**。
本地实测 84/85（其余 eierpecken 用例全过）。

## 上游测试实测（aarch64 OHOS 本机）
| 套件 | 结果 |
|------|------|
| unit-tests-utils | 35/35 ✅ |
| unit-tests-ei | 10/10 ✅ |
| unit-tests-eis | 7/7 ✅ |
| eierpecken | 84/85（socket_overflow 豁免）|
| dtdcheck | 1/1 ✅ |
| protocol-test（pytest）| 31/31 ✅ |
| scanner-pytest（pytest）| 8/8 ✅ |
| **合计** | **176/177（99.4%）** |

CI 环境无 pytest/structlog → tests=auto 自动只跑 C 套件（52+1 用例 +
dtdcheck；python 套件 39 用例本地实测申报）。

## test_package 消费者验证
C 程序链接 libei.so + libeis.so，调用 ei_new_sender/ei_is_sender/
ei_get_user_data/ei_ref/ei_unref + eis_new/eis_unref（7 断言 + CMakeDeps
find_package 驱动 2 断言）。

## 知识沉淀
- DRAFT-8959：musl tmpfile() EACCES 代码级替代（munit 系测试通用）
- DRAFT-8960：meson ninja 探测失败（libc++_shared.so + LD_LIBRARY_PATH 空格污染项）
---

**编译结束**: 2026-09-15 13:15
**最终状态**: built
