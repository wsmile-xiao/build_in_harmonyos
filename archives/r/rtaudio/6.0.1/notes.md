# rtaudio 6.0.1 适配笔记

## 来源
- 上游: https://github.com/thestk/rtaudio tag 6.0.1（tag 无 v 前缀）
- sha256: 7206c8b6cee43b474f43d64988fefaadfdcfc4264ed38d8de5f5d0e6ddb0a123

## 选型与查重
- 依赖拓扑 POTENTIAL_SIMPLE 候选（roots: cubicsdr/0.2.7 等 2 个 pending 任务依赖
  librtaudio-dev）；仓库 archives/ 与近 2500 条 PR 无 rtaudio 任何版本 → 首次适配。
- 知识查重（四作用域）：命中 E285（音频库无音频后端环境：关闭外部后端+
  内置 Null/loopback 后端+替代验证）——与本适配同构，REUSE_EXISTING 不新建草稿；
  E472（SDL dummy headless 替代验证先例）佐证边界断言口径。查重证据见
  knowledge-dedup-result.json。另：本任务远端对未发布依赖返回加速策略报错的
  现象与 E477 一致（流程注记）。

## 平台边界（核心决策）
- OHOS 无 ALSA/JACK/Pulse/OSS 音频栈：配方将全部 RTAUDIO_API_* 显式 OFF。
- RtAudio.h 在未收到任何后端定义时自动定义 __RTAUDIO_DUMMY__（源码注释
  "A compilable but non-functional API"）：库完整编译/链接/安装，
  运行期 getDeviceCount()==0、getCurrentApi()==RTAUDIO_DUMMY。
- 可验证边界 = 编译链接 + API 枚举含 dummy + 设备数为 0 的确定性断言；
  真实音频回放/录音属平台边界外，不在测试声明中伪装为已验证。
- pthread：OHOS musl 并入 libc，CMake Threads::Threads 在 sysroot 解析为
  空档案，链接无冲突（与 E543/E099 同族事实）。

## 适配方式
- CMake 构建（上游自带完整 install 规则：lib/头文件/cmake config/pkg-config）。
- test_package：消费者边界断言 4 条（见 test_package/MANIFEST.yml），CI 原生执行。

## 验证记录
- r1: 本机 Windows 交叉构建环境 conan create（clang 15 / libc++ / OHOS armv8）
  + ohc conan-verify（G0-G4）；W3 本地 CI；测试执行由 CI 原生 arm64 完成
  （本地交叉宿主以 tools.build:skip_test 构建级验证，与 CI 分工如实披露）。

## 结束

最终状态：built（本机 W3 全绿；测试执行与发布以 CI 原生 arm64 为准）。
