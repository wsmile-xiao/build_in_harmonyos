# mkinitfs 3.4.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
make WITH_NLPLUG=0 PREFIX=$DEFAULT_PREFIX
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | nlplug-findfs 依赖不可用 | OHOS 不提供 nlplug-findfs 工具 | 设置 WITH_NLPLUG=0 禁用 nlplug-findfs 相关功能 |

## 交付物

| 文件 | 说明 |
|------|------|
| mkinitfs-3.4.5-ohos-aarch64.tar.gz | 预编译包 |
| mkinitfs-3.4.5-ohos-aarch64-debug.tar.gz | debug 符号包 |

---

**编译结束**: 2026-06-01
**最终状态**: built