# liblxi 1.22 适配笔记

## 编译环境
- 构建系统: meson（上游 meson_version >= 0.53.2，设备 meson 1.12.0）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（/data/service/hnp/bin），llvm-ar/llvm-ranlib
- 状态: built（conan-verify G0/G1/G2/G3/G4 + L2/L4/L5 全过）

## 编译步骤

conan create（ohos-aarch64 profile，static 交付）：
1. source(): 下载官方 v1.22 tarball（sha256 校验）
2. generate(): MesonToolchain，弹出 AR/AS/STRIP/NM/RANLIB 环境变量并
   锁定绝对路径（CI worker 导出 llvm-* 裸名导致 meson archiver 探测失败，
   同 at-spi2-core 2.60.5 配方）；PkgConfigDeps 生成 libxml-2.0.pc /
   libtirpc.pc 供 meson dependency() 解析
3. build(): meson configure + build（-j2）
4. package(): meson install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 src/meson.build 硬编码 shared_library('lxi')，default_library 不生效，产物恒为 .so | 上游写死 | 补丁 0001：shared_library → library()，配方 shared 选项（默认 static，R26）真实生效 |
| 2 | test_package 链接报 `undefined symbol: pthread_cancel` | OHOS musl 无 POSIX 线程取消 API（知识库 E085）；vxi11.c 超时路径用 pthread_cancel 回收 worker | 补丁 0002（E513 guarded-signal-thread-exit）：weak 声明链接期探测——glibc 走真 cancel；缺席时 pthread_once 安装 SIGRTMIN handler（pthread_exit），pthread_kill 定向触发，保住 join 语义；无平台宏 |
| 3 | 首轮 resign 步骤 `binary-sign-tool` 报 Error 127 | 重签步骤对已签产物重复签名；实测 meson install 保留 .codesign | 移除重签步骤（llvm-readelf -S 实测安装件 .codesign=1），无 ELF 运行时改写 |
| 4 | meson 依赖解析 libxml-2.0/libtirpc | conan 包需 pkg-config 桥接 | generators = PkgConfigDeps（同 at-spi2-core 已验证模式） |

## 源码修改

均为 patches/ 补丁（conandata.yml 声明）：
- 0001-ohos-meson-library.patch：src/meson.build 一行（shared_library → library）
- 0002-ohos-pthread-cancel-signal-exit.patch：src/vxi11.c，新增
  _thread_cancel 兼容层（weak 探测 + SIGRTMIN handler），两处调用点
  pthread_cancel → _thread_cancel

## 依赖版本

- libtirpc/1.3.7（VXI-11 SunRPC；musl 无 rpc/rpc.h）
- libxml2/2.15.3.1（vxi11.c 解析 HTTP 定位信息）
- 线程：meson dependency('threads')（系统）
- avahi-client：可选（required: false），OHOS 无 avahi 头 → mDNS 发现降级为空实现（上游原设计）

## 验证结果

- conan create + conan-verify：PASS（G0/G1/G2/G3/G4，L2 平台功能矩阵、L4 checksec、L5 产物基线）
- 消费者测试（真机）：test_liblxi 12/12 断言通过（lxi_init/lxi_connect(RAW 回环)/
  lxi_send/lxi_receive/lxi_disconnect 全链路，ctest: 100% tests passed）
  日志：reports/conan-create.log、test_package/build/.../Testing/Temporary/LastTest.log

## 上游测试清点（R51）

- meson.build 仅 subdir('src')/subdir('man')，无 test/meson.build，
  `meson test --list` 为空 → 注册测试 N_static = 0
- test/ 下 4 个未注册示例程序（search.c / search-mdns.c / scpi.c /
  receive-image-data.c）需局域网真实 LXI 仪器（mDNS 发现或对某 IP 的
  SCPI 会话），设备与 CI 均无仪器，无法运行，逐项原因同 PR 正文

## 注意事项

- liblxi 非系统同名库（R26 不受限），但默认 static 交付以规避 .so 运行时
  签名/RPATH 一类问题；shared=True 可构建出 liblxi.so
- E090（host_system == 'harmonyos' 风险）对本包不适用：meson.build 只做
  cygwin/darwin 分支，无 == 'linux' 判断
- test_package/build/ 为本地验证产物，提交前需剔除
---

**编译结束**: 2026-09-18 02:37
**最终状态**: built
