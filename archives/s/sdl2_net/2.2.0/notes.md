# sdl2_net 2.2.0 适配笔记

## 编译环境
- 构建系统: cmake（autotools configure 因临时文件权限问题失败）
- 编译日期: 2026-05-26
- 编译器: clang/clang++ 15.0.4
- 状态: built（编译成功，待验证）

## 编译步骤

1. 修改 config.guess/config.sub 添加 OpenHarmony (ohos) 平台识别
2. 安装 SDL2 2.30.0 预编译包（wget + tar 解压到 ~/usr/local）
3. 使用 CMake 构建（避开 autotools configure 临时文件权限问题）：
   ```bash
   mkdir -p build-cmake && cd build-cmake
   cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=~/usr/local
   make -j2 && make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | OpenHarmony 系统名 "HarmonyOS" 不在支持列表 | 添加 HarmonyOS 分支返回 aarch64-unknown-linux-ohos |
| 2 | config.sub 验证三元组失败 | ohos 不在 OS/kernel-os 白名单 | 添加 ohos* 到 OS 白名单、linux-ohos* 到 kernel-os 白名单 |
| 3 | 缺少 SDL2 依赖 | SDL2_net 需要 SDL2 >= 2.0.4 | 安装 SDL2 2.30.0 预编译包 |
| 4 | autotools configure 临时文件权限拒绝 | config.status 尝试创建 ./confaODHFP/subs1.awk 失败 | 改用 CMake 构建系统 |

## 源码修改

- config.guess: 添加 HarmonyOS 识别（第152行后）
- config.sub: 添加 ohos 支持（3处修改）

## 依赖版本

- SDL2 2.30.0（预编译包）

## 验证结果

```bash
ls -la ~/usr/local/lib/libSDL2_net.so
# -rwxrwx--- libSDL2_net.so (35KB)

ls -la ~/usr/local/include/SDL2/SDL_net.h
# -rw-rw---- SDL_net.h (37KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libSDL2_net.so | 35KB | SDL2 网络库共享库 |

## 注意事项

- autotools configure 在 OpenHarmony 上可能遇到临时文件权限问题，建议优先使用 CMake
- pkg-config 文件 SDL2_net.pc 中 Libs 字段重复，不影响实际使用
---

**编译结束**: 2026-05-26 20:44
**最终状态**: built
