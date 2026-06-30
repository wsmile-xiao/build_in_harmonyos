# opencore-amr 0.1.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 缺少 HarmonyOS 平台检测分支 | 添加 `*:HarmonyOS:*:*` 识别为 `aarch64-unknown-linux-ohos` |
| 2 | config.sub 不识别 linux-ohos | 缺少 ohos 三元组支持 | 在多处添加 `linux-ohos*` 和 `ohos*` 支持 |

## 源码修改

- `0001-config.guess.patch`: 添加 HarmonyOS 平台检测，识别为 aarch64-unknown-linux-ohos
- `0004-config.sub.patch`: 在 linux-* 匹配列表、OS 验证、kernel-os 组合验证中添加 ohos 支持

## 依赖版本

无外部依赖

## 验证结果

Quality 门禁全部 PASS (G1-G4)

## 交付物

| 文件 | 说明 |
|------|------|
| opencore-amr-0.1.6-ohos-aarch64.tar.gz | 预编译包（含 ELF 签名） |
| opencore-amr-0.1.6-ohos-aarch64-debug.tar.gz | debug 符号包 |

---

**编译结束**: 2026-05-26 12:41
**最终状态**: built