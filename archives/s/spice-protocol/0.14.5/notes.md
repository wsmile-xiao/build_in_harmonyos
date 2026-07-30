# spice-protocol 0.14.5 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build spice-protocol 0.14.5 --url=https://www.spice-space.org/download/releases/spice-protocol-0.14.5.tar.xz
```

### 2. 配置与编译
spice-protocol 使用 meson 构建系统。需要设置正确的环境变量：
```bash
export PATH="/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:$PATH"
export CC="/storage/Users/currentUser/usr/local/bin/cc"
export AR="/data/service/hnp/bin/llvm-ar"

cd /storage/Users/currentUser/builds/spice-protocol-0.14.5.work
meson setup builddir --prefix=$HOME/usr/local
ninja -C builddir
ninja -C builddir install DESTDIR=$HOME/tmp/test-install-spice-protocol-0.14.5
```

### 3. 打包与归档
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish spice-protocol 0.14.5 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 C 编译器 | PATH 中没有包含编译器路径 | 添加 `/storage/Users/currentUser/usr/local/bin` 到 PATH，设置 CC 环境变量 |
| 2 | meson 找不到链接器(ar) | llvm-ar 不在 PATH 中 | 添加 `/data/service/hnp/bin` 到 PATH，设置 AR 环境变量 |

## 源码修改

无需修改源码，纯头文件包。

## 依赖版本

- meson: 1.11.1
- ninja: 1.13.1
- pkg-config: 0.29.2

## 验证结果

```bash
# 验证 pkg-config 文件
pkg-config --modversion spice-protocol
# 输出: 0.14.5

# 验证头文件安装
ls $HOME/usr/local/include/spice-1/spice/
# 输出: barrier.h enums.h ipc_ring.h macros.h protocol.h qxl_dev.h qxl_windows.h start-packed.h stats.h stream-device.h types.h vd_agent.h end-packed.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| spice-protocol-0.14.5-ohos-aarch64.tar.gz | 10KB | 预编译包（头文件和 pkg-config 文件） |

## 注意事项

1. spice-protocol 是纯头文件包，无二进制产物，打包时只包含头文件和 pkg-config 文件
2. meson 需要正确设置 CC 和 AR 环境变量，确保编译器和链接器在 PATH 中
3. G0 干净构建验证可能因 tar 解压 xz 格式问题失败，但实际编译已通过

## Conan 适配验证

- 源码 SHA256: `baf58449f6e89d19f475899ad5fb9196fdc46c03cc53233f4e39cf2978f9cff7`
- 包类型: `header-library`
- 包 ID: 清除编译器、构建类型和架构差异
- 打包内容: 13 个协议头文件、BSD 许可证、可重定位 `spice-protocol.pc`
- 消费者测试: 编译并运行 `test_spice_protocol.c`，验证 5 项协议结构和常量
- Linux x86_64 / GCC 11 / Conan 2.29.1: `conan create` 通过
- 破坏性负向测试: 移除 `include/` 后消费者编译失败，确认测试真实依赖包产物
- HarmonyOS PC aarch64 / Clang 15.0.4 / Conan 2.29.1: `conan create` 通过
- CI 门禁: L0、L1、L4 通过，L2 因无可执行文件跳过，L5 因纯头文件包无 `bin/` 或 `lib/` 给出非阻断警告
- 真机 pkg-config: `--modversion` 返回 `0.14.5`，`--cflags` 返回可重定位的 `include/spice-1` 路径

## 知识提取

本次编译无新的错误模式需要沉淀到知识图谱。
---

**编译结束**: 2026-05-26 20:25
**最终状态**: published
---

**编译结束**: 2026-05-26 21:37
**最终状态**: published
