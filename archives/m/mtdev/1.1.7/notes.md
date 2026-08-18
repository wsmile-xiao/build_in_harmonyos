# mtdev 1.1.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 mtdev-1.1.7.tar.gz
2. 应用 config.guess 和 config.sub 补丁以识别 HarmonyOS 平台
3. 运行 configure --prefix=... --enable-static --disable-shared
4. make -j1 && make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 上游 config.guess 无 HarmonyOS 枚举 | 添加 HarmonyOS 到 UNAME_SYSTEM case 和 aarch64:HarmonyOS 分支 |
| 2 | config.sub 不识别 linux-ohos | 上游 config.sub 无 ohos OS 和 linux-ohos 内核组合 | 添加 ohos 到 OS 列表和 linux-ohos 到内核-OS 组合验证 |
| 3 | configure 中 umask 077 导致 HMDFS 目录无法写入 | 鸿蒙 HMDFS 文件系统下 umask 077 创建的目录无法被其他进程写入 | 在 conanfile.py build() 中将 `umask 077 && mktemp -d` 替换为 `mktemp -d` |
| 4 | test.c 中 mtdev_has_mt_event 空指针解引用 | memset 清零后 dev.state 为 NULL，mtdev_has_mt_event 直接访问 dev->state->mt_event | 重构测试，移除对 mtdev_has_mt_event 的调用，改用 mtdev_close 和 mtdev_new_open 验证 API 链接 |

## 源码修改

- `patches/0001-config-aux-config.guess.patch`: 添加 HarmonyOS 平台识别到 config.guess
- `patches/0002-config-aux-config.sub.patch`: 添加 ohos OS 和 linux-ohos 内核组合到 config.sub

## 依赖版本

无外部依赖，mtdev 仅依赖 Linux 内核 input event 接口。

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# Conan test_package: 通过
# L0 门禁: 通过
# L1 门禁: 通过
```

## 注意事项

- mtdev 是 libinput 的依赖库，用于处理多点触控设备输入事件转换
- 构建为静态库（--enable-static --disable-shared）
- 测试包验证 API 链接和结构体布局，不依赖真实触控设备
