# libgpiod 2.1.3 — 编译进度

> 档案创建时间: 2026-04-29
> 最后更新: 2026-04-29
> 状态: ✅ built

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libgpiod |
| 版本 | 2.1.3 |
| 构建系统 | autotools |
| 编译器 | clang |
| 源码路径 | https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git |

## 二、编译阶段

### Phase 1: 环境准备 ✅
- [x] ohc-run.py init-build 完成

### Phase 2: 编译 ✅
- [x] configure 完成（--prefix=$DEFAULT_PREFIX）
- [x] make 编译完成
- [x] make install DESTDIR=$TEST_PREFIX 完成

### Phase 3: 测试验证
- [x] 编译产物验证通过

### Phase 4: 预编译包制作 ✅
- [x] 预编译包生成: libgpiod-2.1.3-ohos-aarch64.tar.gz

## 三、关键修复

| 问题 | 知识图谱 | 解决方案 |
|------|---------|---------|
| HMDFS umask 077 | E011 | sed -i 's/umask 077/umask 022/g' configure |
| config.guess 不识别 HarmonyOS | E007 | 添加 HarmonyOS 检测分支 |
| musl 缺 versionsort | - | 在 tools/tools-common.c 添加兼容实现 |

## 四、补丁文件
- 0001-config-guess.patch
- 0002-config-sub.patch
- 0003-configure-umask.patch
- 0004-versionsort-compat.patch

## 五、产物
- libgpiod.so.3.1.2 (108KB)
- libgpiod.a (178KB)
- 工具: gpiodetect, gpioinfo, gpioget, gpioset, gpiomon, gpionotify