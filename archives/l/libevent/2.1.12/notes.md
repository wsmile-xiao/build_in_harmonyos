# libevent 2.1.12 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码并解压
2. 应用 5 个补丁（config.guess/config.sub 平台检测 + configure umask 修复 + 测试文件路径修复）
3. `./configure --prefix=... --disable-openssl`（AutotoolsToolchain 自动处理，openssl 可选已禁用）
4. `make -j1`（HMDFS 上 mkfifo 需 -j1）
5. `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 临时目录不可写 | HMDFS umask 077 | 0003-configure.patch: umask 077→022 |
| 2 | 平台不识别 | config.guess/sub 无 OHOS | 0001/0002 补丁添加 HarmonyOS 检测 |
| 3 | make -j2 mkfifo 失败 | HMDFS FIFO 限制 | 使用 make -j1 |
| 4 | test_package 运行时找不到 .so | OHOS LD_LIBRARY_PATH 未设置 | test() 中手动设置 LD_LIBRARY_PATH |

## 源码修改

5 个补丁：
- 0001-build-aux-config.guess.patch — 添加 HarmonyOS 平台检测
- 0002-build-aux-config.sub.patch — 添加 ohos 操作系统支持
- 0003-configure.patch — 修复 HMDFS umask 077 问题 (E011)
- 0004-test-regress.gen.c.patch — 修复测试文件路径引用
- 0005-test-regress.gen.h.patch — 修复测试文件路径引用和宏命名

## 依赖版本

可选系统依赖: openssl 3.5.6（cmd-pkgs 系统包，仅 libevent_openssl 模块需要）。
当前构建已通过 `--disable-openssl` 禁用 SSL 模块，核心库无强制外部依赖。
待 openssl PR (#1732) 合入后可移除禁用标志并启用 event_openssl。

## 验证结果

```
libevent version: libevent-2.1.12-stable
test libevent 2.1.12: OK
```

## 注意事项

- libevent 非系统同名库 (R26)，动态链接由 Conan 管理
- test_package 在 OHOS 上需手动设置 LD_LIBRARY_PATH
