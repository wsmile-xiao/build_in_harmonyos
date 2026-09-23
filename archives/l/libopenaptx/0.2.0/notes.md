# libopenaptx 0.2.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# W0: 零外部依赖（无 conanfile 依赖声明需要检查）
make -j1 CC=clang AR=llvm-ar          # 构建共享库+静态库+openaptxenc/openaptxdec
make install PREFIX=<package_folder>  # lib/ bin/ include/ lib/pkgconfig/
```

上游 Makefile 自带 CFLAGS(-W -Wall -O3)/LDFLAGS(-s)，仅需覆盖 CC/AR（OHOS 无 `cc`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备无法直连 github.com（下载超时） | 设备网络限制 | tarball 经 Windows 侧下载（codeload.github.com，与官方 archive 同字节），scp 到设备；sha256 校验后预置共享 dlcache（`s/<sha256>` + sidecar 登记官方 URL） |

## 源码修改

无补丁。上游 Makefile 原生支持 CC/AR/PREFIX 覆盖，开箱通过。

## 依赖版本

无外部依赖（纯 C99，仅 libc/libm）。

## 验证结果

```bash
# W3 conan create（设备）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # → 全绿，test_package 通过

# 消费者测试（test_package/test.c，链接打包库）
aptx_init/encode/decode 往返：256 帧(24B) → 1024B aptX（4:1 精确）、
编码确定性、解码帧对齐（23 帧编码延迟，与 openaptx.h "90 样本取整到 92" 一致）、
平均单样本偏差 ~0.3%（幅度 100000，断言 <1%）

# 上游测试
无 test/check 目标（N_static=0）
```

## 注意事项

- 上游无自动化测试：Makefile 只有 all/clean/install/uninstall，仓库无测试注册入口
- API 契约（openaptx.h）：输入为 24bit 有符号立体声原始流（24 字节/帧 = LLLRRR×4），
  aptX 4:1、aptX HD 3:1；编码器滞留最后 90 样本（取整到 92 = 23 帧）需 aptx_encode_finish() 冲刷
---

**编译结束**: 2026-09-16 12:47
**最终状态**: built
