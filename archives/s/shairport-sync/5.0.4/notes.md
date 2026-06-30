# shairport-sync 5.0.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang / clang++
- 状态: built

## 编译步骤

1. 下载 shairport-sync 5.0.4 源码 (GitHub release tarball)
2. 运行 autoreconf -fi 重新生成 autotools 文件
3. 运行 configure，指定 --host=aarch64-unknown-linux-ohos
4. 修复 config.guess 和 config.sub 添加 OHOS 支持
5. 添加 ohos_compat.c 兼容层（pthread_cancel stub）
6. 运行 make 编译
7. 运行 make install 安装到 staging 目录
8. 运行 ohc verify-build 质量门禁验证
9. 运行 ohc package 打包预编译包

```bash
# configure 命令
./configure --host=aarch64-unknown-linux-ohos \
  --with-alsa --with-soxr --with-ssl \
  --prefix=$DEFAULT_PREFIX

# 环境变量
export CC=clang
export CXX=clang++
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_cancel/pthread_setcancelstate/pthread_testcancel 未定义 | musl/OHOS 不实现 pthread 取消机制 | 新增 ohos_compat.c，提供 __OHOS__ 条件下的 stub 函数 |
| 2 | config.guess/config.sub 无法识别 OHOS 目标平台 | autotools 标准脚本不含 OHOS 支持 | 替换为支持 OHOS 的版本 |
| 3 | configure 生成的 Makefile 路径问题 | autoreconf 生成文件需要 OHOS 适配 | 重新生成并修补所有 autotools 输出文件 |

## 源码修改

15 个补丁文件:
- 0001-0014: autotools 重新生成的文件（Makefile, configure, config.guess/config.sub 等）
- 0015-ohos_compat.c: 新增 OHOS pthread_cancel 兼容层

关键补丁说明:
- 0002-Makefile.am.patch: 在 shairport_sync_SOURCES 中添加 ohos_compat.c
- 0015-ohos_compat.c.patch: 新建 ohos_compat.c 兼容层文件，为 pthread_cancel 系列函数提供 stub

## 依赖版本

| 依赖 | 版本 | 构建系统 |
|------|------|----------|
| OpenSSL | 3.x | pkg-config |
| soxr | 0.1.3 | cmake |
| alsa-lib | 1.2.x | autotools |
| avahi | 0.8 | autotools |

## 验证结果

```
ohc verify-build shairport-sync 5.0.4
# G1-G4 全部通过，质量报告: PASS
# Runtime verification: PASS
# Binary version output: 5.0.4-OpenSSL-ALSA-soxr
```

## 交付物

| 文件 | 说明 |
|------|------|
| shairport-sync-5.0.4-ohos-aarch64.tar.gz | 预编译包（stripped） |
| shairport-sync-5.0.4-ohos-aarch64-debug.tar.gz | 调试符号包 |

## 注意事项

- ohos_compat.c 兼容层使用 __OHOS__ 条件编译守卫，不影响其他平台
- pthread_cancel 为 no-op stub，线程退出依赖 graceful shutdown（pthread_join）
- AirPlay 1 (classic) 协议模式；AirPlay 2 需额外依赖未包含在本次编译中

---
**编译结束**: 2026-05-26
**最终状态**: built