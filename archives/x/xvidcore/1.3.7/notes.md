# xvidcore 1.3.7 适配笔记

## 编译环境
- 构建系统: autotools (custom configure + Makefile)
- 编译日期: 2026-09-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 下载并解压源码
tar xzf xvidcore-1.3.7.tar.gz
cd xvidcore/build/generic/

# 2. Patch config.sub 添加 linux-ohos 支持
# (详见 patches/0001-build-generic-config-sub.patch)

# 3. 运行 configure（指定 OHOS 三元组）
./configure --prefix=$PREFIX \
    --build=aarch64-unknown-linux-ohos \
    --host=aarch64-unknown-linux-ohos

# 4. 修复 config.status 的 mktemp 问题（HMDFS 权限）
# config.status 使用 mktemp -d "./confXXXXXX" 在 HMDFS 上失败
# 需替换为预创建的可写目录

# 5. 编译
make -j1

# 6. 安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2013 年的 config.guess 不包含 HarmonyOS 分支 | 使用 --build/--host 显式指定三元组 aarch64-unknown-linux-ohos |
| 2 | config.sub 拒绝 linux-ohos 三元组 | config.sub 不识别 ohos 操作系统 | Patch config.sub 添加 linux-ohos 到 maybe_os 和 OS 列表 |
| 3 | config.status 创建临时文件失败 | mktemp -d "./confXXXXXX" 在 HMDFS 上权限不足 | 替换为预创建的可写 TMPDIR 子目录 |
| 4 | SRC_DIR = ../../src 路径无效 | init-build 提升了 build/generic 目录 | 从原始目录结构 build/generic/ 构建 |

## 源码修改

- `patches/0001-build-generic-config-sub.patch` — 在 config.sub 中添加 linux-ohos 支持（2 处修改）

## 依赖版本

无外部依赖。xvidcore 是独立的 C 库，仅依赖系统库 libpthread 和 libm。

## 验证结果

```bash
# 编译成功
make -j1
# 输出: libxvidcore.a, libxvidcore.so.4.3

# 测试
test_package/test_xvidcore
# 输出: xvidcore initialized successfully
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libxvidcore.a | 静态库 |
| lib/libxvidcore.so.4.3 | 动态库 |
| include/xvid.h | 头文件 |

## 注意事项

- xvidcore 源码结构为嵌套式：build/generic/ 含构建文件，../../src/ 含源码
- 无上游自动化测试（make check 不可用），examples/ 有手动测试工具
- 构建产物包含静态库和动态库
---

**编译结束**: 2026-09-06 02:40
**最终状态**: built
