# raxml 8.2.13 适配笔记

## 编译环境
- 构建系统: makefile（手工 Makefile 变体，无 configure / 无 install 目标）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（OHOS aarch64 交叉工具链）
- 状态: built

## 编译步骤

```bash
# 解压源码（GitHub tag v8.2.13；下载时由 CI 自动添加镜像 fallback）
# 直接以 clang 编译顺序版（Makefile.gcc 已含 aarch64 分支）：
make -f Makefile.gcc CC=clang -j1
# 产物: raxmlHPC
```

RAxML 无 configure 脚本，源码自带多套 Makefile 变体
（Makefile.gcc / Makefile.SSE3.gcc / Makefile.AVX.gcc / Makefile.PTHREADS.gcc 等）。
选择顺序版 Makefile.gcc：其内部按 `uname -m` 分支，aarch64 时 `ARCH_CFLAGS=` 为空，
无需 SSE 标志；源码自带 `sse2neon.h`（400KB）处理 x86 SIMD 到 NEON 的翻译。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 v8.2.13 tag 内版本横幅仍为 8.2.12 | 上游发布 tag 时未同步代码内版本字符串（README 亦写 8.2.12） | 消费者测试断言按 "RAxML version 8.2" 系列放宽，PR/notes 如实说明 |
| 2 | conan-init 默认生成 autotools 模板 | raxml 无 configure 脚本，纯 Makefile 构建 | 改用 conanfile-makefile.py.tmpl 重写：application 类型、build 直接 `make -f Makefile.gcc CC=<conan cc> -j1`、package 手动 copy raxmlHPC 到 bin/ |
| 3 | 上游无测试资产 | 源码包无 test 目录 / check 目标 / 测试钩子 / 示例数据 | test_package 自研消费者测试：`raxmlHPC -v` 版本横幅 + 最小 PHYLIP 数据 GTRCAT 最大似然搜索验证生成 RAxML_bestTree |

## 源码修改

无（未改上游源码，无补丁）。

## 依赖版本

- 无外部 conan 依赖（纯 C，仅链接系统 libm `-lm`）

## 验证结果

```bash
# 本地编译
make -f Makefile.gcc CC=clang -j1        # exit 0，生成 raxmlHPC (793KB)

# 运行验证
./raxmlHPC -v                            # 正常输出 "This is RAxML version 8.2.12 ..."（上游版本串未同步）

# 自研消费者测试（test_package/test_raxml.py）
python3 test_raxml.py <package_folder>   # PASS：版本横幅 + ML 搜索生成结果树

# conan-verify（8 道门禁）
ohc-run.py conan-verify raxml 8.2.13     # G1-G4 + L2/L4/L5 全 PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| raxmlHPC | 793KB | 顺序版可执行文件（bin/） |

## 注意事项

- OHOS /tmp 只读：临时文件一律用 `$HOME/tmp`。
- init-build 须设置 `OHC_PROJECT_DIR` 指向工作区仓库（否则归档误写入 SKILL 目录）。
- 上游无 install 目标，package() 必须手动放置二进制。
---

**编译结束**: 2026-09-28 10:45
**最终状态**: built
