# nymphcast 0.2-alpha0 适配笔记

## 编译环境
- 构建系统: Makefile（src/server/Makefile，C++17）
- 编译器: clang/clang++（TOOLCHAIN=clang）
- 上游 tag: v0.2-alpha0 @ commit 3f500599a8e5092280eb8724bbee5ca618634628
- 许可证: BSD-3-Clause
- 状态: built（archive 记录）

## 关键事实

### 构建系统
- 上游**无 CMakeLists.txt**，只有 GNU Make（src/server/Makefile）
- 旧 PR 分支用 cmake.configure() 会失败（源码无 CMakeLists）
- Makefile 支持 `TOOLCHAIN=clang`（toolchain/clang.mk: GPP=clang++, GCC=clang）

### 源码 tarball
- GitHub 动态归档 tarball 哈希非确定（gzip 头时间戳变化）
- conandata.yml 中省略 sha256，Conan 不做哈希校验

### 依赖（ohpcd remote 可用）
- poco/1.15.3 ✓
- ffmpeg/8.1.2 ✓（多版本可用）
- sdl2/2.30.10 ✓
- freetype/2.14.3 ✓
- curl/8.15.0 ✓
- freeimage/3.18.0 ✓
- rapidjson/1.1.0 ✓

### 依赖（ohpcd remote 已发布，recipe requirements() 已声明）
- **nymphrpc/v0.1.1** ✓（archives/n/nymphrpc/v0.1.1/conanfile.py，已发布）
- **libnymphcast/v0.2.1** ✓（archives/l/libnymphcast/v0.2.1/conanfile.py，已发布）
- **sdl2_image/2.6.0** ✓（archives/s/sdl2_image/2.6.0/conanfile.py，已发布）
- **glew**: 不需要（server 不链 glew）
- **ffmpeg**: 6.1.6（上游 ffplay fork 用 legacy avfft.h/av_rdft API，FFmpeg 7+ 移除）

### OHOS 风险
- R3: `-lstdc++fs` — OHOS clang 15 + libc++ 通常不需要
- R4: `-lGL -lasound` 系统库缺失 — Makefile Linux 分支硬链
- R10: `ohos_stub_headers.h` — patch 0003 提供 OHOS compat seam（聚合真实上游头，可编译）
- R8: 代码签名 — OHOS 可执行文件需要 binary-sign-tool

## 补丁

### 0001-src-server-NymphCastServer.cpp.patch（round-8 重生成，最小 diff）
- 上游 v0.2-alpha0 源码树已含 NymphCastServer.cpp（git ls-tree @3f500599 实测，非缺失）
- 本 patch 对既有文件做增量修改：`__OHOS__` 分支走 ohos_stub_headers.h、`#ifndef __OHOS__`
  裁剪 LCDProc 子系统 include/连接块；logFunction 前置声明保持上游无条件声明（不破坏非 OHOS 平台）
- 不再整文件替换，无无关空白归一化；GNU patch / git apply / Conan patch_ng 均可干净应用
- `--version` 选项在 SDL 初始化前返回，适合无头测试

### 0002-src-server-ffplay-sdl_renderer.cpp.patch（round-8 重生成，最小 diff）
- 上游已含 ffplay/sdl_renderer.cpp；仅插入 `__OHOS__` 分支（include ohos_stub_headers.h）
- 不再整文件替换

### 0003-src-server-ohos-stub-headers.h.patch (1KB)
- 新增 src/server/ohos_stub_headers.h（OHOS compat seam）
- __OHOS__ 分支经此 seam 聚合 screensaver.h/nyansd.h/nc_apps.h/gui.h
- 实测：四个真实头文件在 OHOS + recipe 注入 include 路径下均可编译
  （SDL2 子目录、freetype2、nymphrpc、libnymphcast），故 seam 直接复用真实头，
  不重实现 stub，保持 ABI 与 Makefile 编译链接的真实实现一致

## 编译命令

```bash
cd src/server
make TOOLCHAIN=clang -j1
```

## 编译产物

- `src/server/bin/<TARGET>/nymphcast_server` — 接收端主程序

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NymphCastServer.cpp 无法直接编译 | OHOS 平台差异（SDL/gui/LCDProc 子系统头与链接） | patch 0001 在既有上游文件上做 __OHOS__ 增量适配 |
| 2 | SDL renderer 编译错误 | OHOS 平台 SDL2 差异 | patch 0002 适配 |
| 3 | 缺少 nymphrpc/libnymphcast/SDL2_image recipe | 依赖库最初未迁移为 Conan 包 | 已迁移并发布（nymphrpc/v0.1.1、libnymphcast/v0.2.1、sdl2_image/2.6.0），requirements() 已声明 |

---

## round-4/5 更新（2026-08-26）

### 0004-src-server-ohos-pthread-compat.h.patch
- 新增 src/server/ohos_pthread_compat.h：声明 GNU pthread 取消 API
  （pthread_cancel/pthread_setcanceltype/pthread_setcancelstate/pthread_testcancel）
- 依据：OHOS pthread.h 无这些 GNU 扩展声明，但设备 libc 符号存在；lcdapi 依赖它们
- 通过 `-include ohos_pthread_compat.h` 注入每个 TU（build() 中 CXXFLAGS 追加）

### 0005-src-server-gui-app-VolumeControl-ohos.patch
- gui/app/VolumeControl.h 含 `<alsa/asoundlib.h>`（OHOS 无 ALSA）
- 新增 `__OHOS__` no-op 分支（OHOS 定义 __linux__ 但无 ALSA；ALSA mixer 在 OHOS 不使用）

### 0006-src-server-Makefile-ohos-link.patch
- OHOS 链接：去掉 -lstdc++fs/-latomic/-lGL/-lasound（libc++ 有 filesystem；OHOS 无 libatomic/libGL/libasound）
- 链接 no-op GL stub（obj/.../ohos_gl_stub.o，GUI renderer 无头运行）

### 0007-src-server-Makefile-ohos-no-strip.patch（新坑）
- **新坑（new_pits_detected）**：OHOS 上对已链接 ELF 做 `strip -S --strip-unneeded`
  会使可执行文件 exec 失败（EPERM "Operation not permitted"）
- 根因：OHOS 链接器（lld）自动生成 `.codesign` 段（self-sign）；strip 修改文件内容但
  不更新签名 → 内核/加载器内容校验失败 → exec 拒绝
- 证据：同文件 unstripped 可运行（`nymphcast_server --version` → v0.2-alpha0.20241108），
  GNU strip 2.45 与 llvm-strip 均破坏；readelf 程序头一致、.codesign 内容一致
- 修复：Makefile OHOS 分支跳过 strip（`ifneq ($(OHOS),true)`），打包未 strip 二进制
- 注意：打包二进制约 53MB（未 strip），正确性优先于体积

### package() 布局修复
- Makefile 输出 `bin/<triple>/nymphcast_server`（TARGET_BIN 含工具链 triple）
- 原 `copy("nymphcast_server", bin, ...)` fnmatch 不跨目录 → 未打包任何二进制
- 修复：`copy("**/nymphcast_server", bin, ..., keep_path=False)` 递归匹配并压平到 package bin/
- 结果：package/bin/nymphcast_server 存在 → conanrun PATH 可解析 → test() 可运行

### test_package 重写
- 原 test.sh（shell 冒烟）→ 真实 C++ 探针 test.cpp（35 行）
- test.cpp 通过 popen 真实调用打包的 nymphcast_server --version，校验版本横幅
- 编译仅需 libc（无外部 include/lib），conanfile.py 用 clang++ 直接编译

---

## round-8 更新（2026-08-27，web-review finding 修复）

### 源码获取说明（NCF-04，保留 git 源的理由）
- conandata 使用 git 源：gitcode 官方镜像 `gh_mirrors/ny/NymphCast.git` + tag v0.2-alpha0 + 固定 commit 3f500599
- GitHub 动态归档 tarball 的 sha256 非确定（gzip 头时间戳每次变化），Conan 2 get() 无法缓存
- git commit 内容寻址、不可变，可复现 → 无 sha256 是可接受偏差
- 残余风险：mirror 与官方 GitHub 潜在差异 → round-7 已比对 databuffer.h 等关键文件与 GitHub raw 一致，commit 固定不可变，风险可控

### 运行时前置（NCF-07）
- 打包二进制 nymphcast_server 为 Conan 托管动态链接（readelf -d 无 RPATH/RUNPATH；
  NEEDED=Poco/FFmpeg/freetype/curl/freeimage/tiff/libc++_shared/libc）
- 裸跑需 conanrun env 注入 LD_LIBRARY_PATH；CI L2 裸跑 skip 属预期（非缺陷）
- 已在 README 声明运行时前置；未设置 RPATH（依赖库路径在 conan cache 中，绝对路径脆弱）

### 补丁重生成（NCF-01/NCF-02）
- patch 0001/0002 由整文件 new-file 型重生成最小 diff（基于上游 v0.2-alpha0 实际文件）
- 0001 恢复 logFunction 前置声明为无条件（与上游一致），移除 ohos_stub_classes.cpp 错误注释
- 验证：git apply --check / toybox patch --dry-run / Conan patch_ng 均可干净应用；
  应用后文件与旧 patch 产物仅差 logFunction 块（语义等价）与空白

---

## round 收尾更新（2026-08-28，upstream-tests-implement）

### 0008-src-test-test_ffplay_local_file-subtitle_disable.patch
- 上游缺陷：src/test/test_ffplay_local_file.cpp 把 `subtitle_disable` 声明为 `int`，
  与 ffplay/types.h 中 extern 的 `bool` 类型冲突，测试无法编译
- master 与 v0.2-alpha0 均存在；本 patch 改为 `bool subtitle_disable`（最小修复）
- 依据：官方 gitcode 镜像 shallow clone 交叉核验 + 设备实测编译

### 0009-src-test-ohos-test-compat.patch
- 新增 src/test/ohos_server_glue.cpp + src/test/ohos_ffplay_globals.cpp
  （测试专用链接闭包 glue，不参与任何测试断言/判定）
- ohos_server_glue: serverMode/slavePlayMutex/slavePlayCon/startSlavePlayback/
  sendGlobalStatusUpdate/finishPlayback —— 生产构建由 NymphCastServer.cpp 提供，
  src/test 二进制只链接 ffplay 栈，故在测试构建中提供等价定义
- ohos_ffplay_globals: test_screensaver 链接闭包所需的 ffplay 全局块
  （test_ffplay_local_file.cpp 自带这些全局，test_screensaver.cpp 没有）

### conanfile.py 测试接入（howard-hinnant-date 先例：build() 内 target 接线 + 受控 env）
- build() 末尾调用 _build_and_run_upstream_tests()：
  - 构建 test_screensaver、test_ffplay_local_file 两个可编译测试与 client
  - env: SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy LC_ALL=C LANG=C
    + LD_LIBRARY_PATH（全部依赖 lib + OHOS 工具链 libc++_shared.so 目录）
  - 运行并记录真实 exit code 到 <src>/.upstream-tests/logs/，不伪装 PASS
- 结果口径（H3 诚实披露）：
  - test_screensaver：exit 0（PASS），但上游测试从不调用 setDataPath，
    只走 "abort, no images" 路径 —— 不夸大为全功能 PASS
  - test_ffplay_local_file：播放完成后 teardown 挂起（上游 event loop quit push
    被注释、read_thread/audio_decoder 线程泄漏），timeout 后 exit 124 —— 上游缺陷
  - test_file_seeking.sh / test_file_transfer.sh：因 test_server build-blocked
    （stale pre-2021 nymphrpc API + `it` undefined）失败，记录为上游缺陷证据
- 恢复条件：上游修复（subtitle_disable 类型 / teardown 挂起 / nymphrpc API）

## 上游测试全集与执行口径（web-review-4 F-2 补充，2026-08-28）

官方测试全集共 7 项（口径=make -C src/test all）：
- src/test/Makefile 目标：test_databuffer / test_databuffer_mm / test_screensaver /
  test_databuffer_mport / test_ffplay_local_file（5 项）
- 集成脚本：test_file_seeking.sh / test_file_transfer.sh（2 项）

round-11 权威 CI 中 build() 测试接入（_build_and_run_upstream_tests）实际执行 4 项
（证据：ci-round-11/upstream-tests/upstream-tests-summary.txt）：
- test_screensaver：exit 0 —— 上游测试从不调用 setDataPath，仅走 "abort, no images"
  路径，不夸大为全功能通过
- test_ffplay_local_file：timeout 后 exit 124 —— 播放完成后上游 teardown 挂起
  （event loop quit push 被注释、read_thread/audio_decoder 线程泄漏）
- test_file_seeking.sh / test_file_transfer.sh：各 exit 1 —— 依赖 bin/test_server，
  上游 test_server 因 stale pre-2021 nymphrpc API 无法构建

未执行 3 项 databuffer 系（未接入 round-11 build() 测试接线）：
- test_databuffer：编译失败 —— 上游缺陷：test_databuffer.cpp 调用
  DataBuffer::setDataRequestCondition()，而 v0.2-alpha0 与 master 的 databuffer.h
  均无此方法（round-7 三方核验：设备源码 + GitHub raw v0.2-alpha0 + master）
- test_databuffer_mport（bin 名 test_db_mp）：编译失败 —— 上游缺陷：
  NymphLogger 头在 v0.2-alpha0 源码树不存在；官方 Makefile 该 target 缺
  -I../server 导致 ffplay/types.h 找不到；另同 test_databuffer 缺
  setDataRequestCondition
- test_databuffer_mm：round-7 实测可编译且独立运行 exit 0（真实通过）；本轮 build()
  接线未包含 —— 属测试接线覆盖缺口（如实记录，不作为上游缺陷夸大）

用户决定（round-10，2026-08-26T16:01:50Z，choice A）：接受 PARTIAL_FAIL
（ACCEPTED_GAP）；恢复条件=上游修复 setDataRequestCondition 或用户接受缺口。
---

**编译结束**: 2026-09-03 14:51
**最终状态**: built
