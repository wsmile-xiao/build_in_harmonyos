# librecast 0.11.2 W0 报告（依赖发布检查 + 静态分析）

**日期**: 2026-09-19
**分支**: feat/librecast-0.11.2（worktree D:\harmonyos\worktrees\librecast）
**结论**: 前置适配就绪；真机构建阻塞于依赖 lcrq 未发布

## W0 依赖发布检查

```sh
conan list "libsodium/*" -r=ohpcd   # → 1.0.20, 1.0.22 ✅
conan list "lcrq/*" -r=ohpcd        # → 0 条 ❌
```

| 依赖 | 版本 | 制品仓 | 说明 |
|------|------|--------|------|
| lcrq | 0.4.1（上游最新 tag） | 未发布 | src/Makefile.in:41 无条件 `LIBS += -llcrq` → 硬依赖，需独立适配 PR |
| libsodium | 1.0.22 | 已发布 | 加密能力；bare-ref 消费惯例 |
| blake3 | —（vendored） | 不适用 | libs/blake3 源码内置（~/src/BLAKE3 仅为 update 目标） |
| libmld | —（vendored） | 不适用 | libs/libmld AC_CONFIG_SUBDIRS 子构建，随主库 |

## 源码

- URL: https://codeberg.org/librecast/librecast/archive/v0.11.2.tar.gz（官方仓库 tag 归档）
- sha256: 62dd9c3250c8e3ef30ed66aa82060d8651e3e887a085079431aa71d4232ce49c（两次下载一致）
- 归档含符号链接（test/all、test/tsan、test/enc），真机解包正常，Windows 本机解包丢链接

## 构建系统分析

- autotools：configure.ac（AC 2.71）+ 预生成 configure + 非 automake 的手写 Makefile.in
- 构建链：顶层 `all: src` → `src: libs` → libs/{blake3→libblake3.a, libmld→*.o} →
  src/*.o + libmld 对象 → `librecast.so`（SONAME librecast.so.0.6）
- **仅共享库产物**，无静态目标；Makefile 非 VPATH 感知 → 必须 in-tree 构建
- 顶层 `install: all doc`：doc 会用裸 `install` 装 man 页（OHOS 无此命令）→ 补丁裁剪
- 构建/安装期多处 `ln -sf` → 补丁改为 `cp -f`（真机符号链接受限）

## 平台兼容性静态检查（configure.ac）

- 必需头文件（arpa/inet.h、netinet/in.h、sys/socket.h 等）：bionic 均有 ✅
- 必需函数（clock_gettime、realpath、strndup、strtoull 等）：bionic 均有 ✅
- 信号量：仅未命名 sem_init/sem_wait（无 sem_open/mq_open/shm_open）✅
- arc4random_uniform：bionic 提供 ✅（-bsd 探测失败亦非致命）
- epoll_create1/recvmmsg：bionic 提供 ✅
- if_linux.c（netlink）：linux/netlink.h 头检测为可选分支，失败则回退 if.c ✅
- libmld 子构建 `SHELL := bash`：真机需有 bash ⚠️（首轮验证确认）

## 测试体系（上游）

- 126（librecast）+ 11（libmld）独立用例；断言 ≈1433；blake3 test 为空目标
- runner：maketest；退出码 0=PASS / 1=WARN / 2=FAIL；网络不满足 → WARN 优雅跳过；
  非 root 权限用例提前退出(0)
- 真机预期：纯 API 用例 PASS，网络/权限类 WARN；如超时改 TEST_PROGS 子集

## 本轮交付物

- archives/l/librecast/0.11.2/conanfile.py、conandata.yml
- archives/l/librecast/0.11.2/patches/0001..0007（dry-run 验证通过）
- archives/l/librecast/0.11.2/test_package/（conanfile.py、CMakeLists.txt、test.c、MANIFEST.yml）
- archives/l/librecast/0.11.2/manifest.yaml（status: pending）、notes.md、本报告

## 验证状态

| 项 | 结果 |
|----|------|
| 源码 URL/sha256 确定性 | ✅ 两次下载一致 |
| 补丁 dry-run | ✅ 7/7 通过 |
| conan export / 配方语法 | ✅（见下轮验证记录） |
| test_package 实质断言 | ✅ 生命周期 + socketpair，非空壳（R34） |
| 真机构建 | ⏸ 阻塞：lcrq/0.4.1 未发布 |
| shadow CI 单包 | ⏸ 待真机轮 |
