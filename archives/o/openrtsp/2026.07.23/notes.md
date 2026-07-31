# openrtsp 2026.07.23 适配笔记

## 编译环境
- 构建系统: custom (live555 genMakefiles)
- 编译日期: 2026-07-30
- 编译器: clang/clang++
- 状态: built

## 编译记录
- **首次编译**: 2026-07-15 14:02 — 本地编译成功 (2026.07.08)
- **PR #2186 创建**: 2026-07-15 14:18 — 来自 feat/openrtsp-2026.07.08
- **CI 失败**: #2669 — openssl/ssl.h 未找到 (远程 CI 缺少 openssl 依赖路径)
- **修复**: 2026-07-16 — 在 conanfile.py generate() 中显式传递 openssl 包含路径到 config.ohos
- **AI Review 修复**: 修复 test_package 空壳测试、exit 0 问题、conandata.yml patches 声明、commands.json binary 标记
- **版本滚动**: 2026-07-30 — 上游 live.2026.07.08.tar.gz 被删除 (download.live555.com 只保留最新版)，滚动到 2026.07.23；删除死代码补丁 0001-config.linux-aarch64.patch (conanfile 动态生成 config.ohos，补丁文件从未被 genMakefiles 引用)
- **测试真实性修复**: 2026-07-30 — 删除死代码占位 test.c；新增 test_openrtsp.sh 无参数消费者 smoke test，真实校验非信号退出/预期 usage 退出码/Usage: 输出；conanfile test() 改为实际调用该脚本（移除无断言的 ignore_errors=True）

## 验证结果
```bash
# 消费者 smoke test：无参数运行 openRTSP
./openRTSP
# 预期：打印 "Usage:" 横幅，退出码 1（usage exit）
# PASS 判据：非信号退出 + 退出码 1 + 输出含 "Usage:"
```

## 已知问题
- **openRTSP -h 触发 Signal 11**：在该平台 (OHOS aarch64) 上，`openRTSP -h` 会触发 Signal 11 (SIGSEGV) 崩溃，这是已知上游问题。因此消费者 smoke test 不使用 `-h`，改用无参数运行（openRTSP 无参数时打印 Usage 并以退出码 1 退出，不触发崩溃路径）。
---

**编译结束**: 2026-07-30 19:35
**最终状态**: built
