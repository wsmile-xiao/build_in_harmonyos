# libdnet 1.12 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 GitHub dugsong/libdnet 仓库获取 libdnet-1.12 tag 源码
2. 应用平台适配补丁 (config.guess, config.sub, configure, tun-linux.c)
3. 运行 `./configure --prefix=$DEFAULT_PREFIX`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. `make check`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 上游无 OHOS 平台检测 | 添加 *:HarmonyOS:*:* case 分支 (patch 0001) |
| 2 | config.sub 不支持 linux-ohos | 上游无 OHOS OS 支持 | 添加 linux-ohos* 到 maybe_os 列表 (patch 0002) |
| 3 | configure Permission denied | HMDFS 文件系统下 umask 077 创建的目录无法写入文件 | 修改 umask 077 → umask 000 并使用 $TMPDIR (patch 0003) |
| 4 | tun-linux.c 编译失败 | linux/socket.h 重定义 sockaddr_storage | 添加 #define _UAPI_LINUX_SOCKET_H 防止重定义 (patch 0004) |

## 源码修改

- patches/0001-config-config.guess.patch: 添加 HarmonyOS 平台检测
- patches/0002-config-config.sub.patch: 添加 linux-ohos OS 支持
- patches/0003-configure.patch: 修复 HMDFS 文件系统 umask 077 权限问题
- patches/0004-src-tun-linux.c.patch: 修复 sockaddr_storage 重定义冲突

## 依赖版本

无外部依赖，仅使用系统 API

## 验证结果

```bash
make check  # 全部通过
conan-verify G0-G4: PASS
W3 本地 CI 模拟: PASS
```

## 注意事项

- libdnet 1.12 使用 autotools (configure + make)，1.17+ 版本改用 CMake
- 库名为 dnet (lib 前缀是 Unix 约定)，conanfile.cpp_info.libs = ["dnet"]
- 头文件安装在 include/dnet/ 目录下

**最终状态**: built
**编译结束**: 2026-08-10
