# libmpeg2 0.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built（2026-10-06 新 Conan 配方已真机验证，尚未通过比赛 PR CI）

## 编译步骤

```bash
# 初始化构建
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmpeg2 0.5.1
source .build-context-libmpeg2-0.5.1

# 配置和编译（DESTDIR 模式）
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j2 && make install DESTDIR=$TEST_PREFIX

# 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package libmpeg2 0.5.1

# 完成
python3 $SKILL_ROOT/scripts/ohc-run.py finish libmpeg2 0.5.1 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS umask 问题 | HMDFS 文件系统默认 umask 077 导致权限问题 | `sed -i 's/umask 077/umask 022/g' configure` |
| 2 | config.guess 过时 | 自带的 config.guess 不识别 OHOS | 更新 .auto/config.guess 到最新版本 |

## 源码修改

应用了 2 个补丁：
1. `0001-.auto-config.guess.patch` - 更新 config.guess 以支持 OHOS 平台
2. `0002-configure.patch` - 修复 HMDFS umask 问题

## 依赖版本

- 无外部依赖

## 验证结果

```bash
# Staging 验证
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/
# 输出: libmpeg2.so.0.1.0, libmpeg2convert.so.0.0.0 等库文件

ls -la $TEST_PREFIX/$DEFAULT_PREFIX/include/
# 输出: mpeg2dec/mpeg2.h, mpeg2dec/mpeg2convert.h 等头文件

# 打包产物验证
tar -tzf libmpeg2-0.5.1-ohos-aarch64.tar.gz
# 包含: bin/mpeg2dec, bin/extract_mpeg2, bin/corrupt_mpeg2
#       lib/libmpeg2.so*, lib/libmpeg2convert.so*
#       include/mpeg2dec/*.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmpeg2-0.5.1-ohos-aarch64.tar.gz | 1.7MB | 发布版（优化编译）|
| libmpeg2-0.5.1-ohos-aarch64-debug.tar.gz | 1.1MB | 调试版 |

## 质量门禁结果

- G0 (干净构建验证): ⚠️ WARNING - Python subprocess 平台限制，已手动验证通过
- G1 (二进制完整性): ✅ PASS
- G2 (功能可用性): ✅ PASS
- G3 (可移植性): ✅ PASS
- G4 (档案完整性): ⚠️ WARNING - manifest 补丁数已修正

## 注意事项

1. 补丁 `0002-configure.patch` 修复了 HMDFS 文件系统的 umask 问题，这是 OpenHarmony 环境特有的问题
2. 补丁 `0001-.auto-config.guess.patch` 更新了 config.guess 脚本以正确识别 OHOS 平台

## 2026-10-06 Conan 适配与上游测试

旧归档只证明手动安装，且源码 URL 是目标机本地文件。本次新增 Conan 2
配方，改用官方 VideoLAN 源码 URL 与 SHA-256；在 `source()` 中应用
`config.guess`/`config.sub` 的 `linux-ohos` 补丁后再让 Conan 复制源码。
旧版 `config.sub` 需要同时识别 kernel-OS、CPU 类型和 OS 白名单；不能把
HarmonyOS 假报为普通 `linux-gnu`。此外，真机工具位于用户目录，和比赛
worker profile 的 `/data/service/hnp/bin` 不同，真机验证只使用任务私有
profile，不修改 CI profile。

上游 `test/tests` 共 73 条，外部测试素材由 SHA-256 固定的项目 CVS 快照
恢复，并在 `build()` 中完整执行：68 条检查 MD5 与 dump，5 条遵循上游
`IGNORE-MD5` 只检查 dump。严格脚本要求 73/73，不能靠上游 shell 的
退出码掩盖缺文件。`libmpeg2-w3-20261006T031522Z` 的同一次
`conan create` 中，73/73 回归和独立 C 消费者均通过；12 个事务阶段也
通过。比赛 worker 的 PR CI 尚未执行，不能标为 published。

---
**编译结束**: 2026-05-29 14:30
**旧版手动归档当时状态**: published（仅指 2026-05-29 手动产物；2026-10-06 Conan 配方仍为 built，比赛发布待 PR 合并后执行）
---

**编译结束**: 2026-05-29 14:31
**最终状态**: built

## 2026-10-10 rule12 消费者补强

此前消费者只检查 API 初始化，且 PR 将其全部列入集成测试，使鸿蒙特有
测试行为 0。当前以同一官方 CVS 快照中的 605 字节完整码流为输入，在
已安装包上执行文件读取、12 帧解码、RGB24 转换、参考像素摘要校验、PPM
输出和回读、资源清理。源码内嵌素材不需要消费者运行时下载，完整流程
只计 1 个用例；上游仍为 73 条，合计 74 条。

独立 x86 上游构建提供可移植 C 解码路径的参考像素；该消费者固定
mpeg2_accel(0)，默认加速路径仍由上游回归验证。实际图像 12×12，转换
缓冲宽度对齐到 16，逐行按真实步长拷贝有效像素，不能按显示宽度连续取帧。

新真机事务 libmpeg2-w3-20261010T023245Z 的独立 Conan create、上游
73/73 和完整消费者 1/1 均 PASS，12 阶段含 release/postrelease 完成。
日志 SHA-256 为 379cc3ce8749d03385489b00162453e630dbdf6b314e86dcbb45affa8554c9bf。
本轮不触发 CI rebuild，不宣称审核通过或制品已发布。
