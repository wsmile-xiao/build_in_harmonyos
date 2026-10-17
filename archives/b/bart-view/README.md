# bart-view 0.3.00 — HarmonyOS PC (OHOS aarch64) 编译记录

## 概述

`bart-view`（[mrirecon/view](https://github.com/mrirecon/view)）是 BART
（Berkeley Advanced Reconstruction Toolbox，MRI 重建工具箱）的配套图像查看器，
构建两个可执行文件：

- `view` — GTK3 多维图像查看器；
- `cfl2png` — 将 BART 的 CFL 数据集（`.hdr` + `.cfl`）导出为 PNG。

**编译状态**: ✅ 编译通过，本地 CI 模拟（conan create + L0–L5）全绿。

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel 1.11.0 aarch64 |
| 编译器 | clang 15.0.4（OHOS SDK） |
| C 库 | musl libc |
| Conan | 2.29.1（OHOS 适配版） |
| 构建系统 | 裸 Makefile |
| 关键依赖 | gtk/3.24.43、libpng/1.6.58、fftw3f/3.3.9、openblas/0.3.33 |

## 编译步骤

```bash
conan create archives/b/bart-view/0.3.00 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd
```

产物：`bin/view`、`bin/cfl2png`（已 ELF 签名）。

## 关键适配点

1. **BART 工具箱 vendored**：bart-view 的 Makefile 通过 `BART_TOOLBOX_PATH`
   链接 BART 的静态库（`libmisc.a`/`libgeom.a`/`libnum.a`）并包含其头文件。
   制品仓的 `bart/1.0.00` 是 application 包，只导出 `bin/bart`，不提供头文件与
   静态库，无法用于链接 → 按仓库既有 vendored 先例（flann/deltarpm/laundrify-aio）
   在构建期下载 BART v1.0.00 官方源码并就地构建所需静态库。详见 `notes.md`。
2. **clang 严格性修复**：BART 源码在 GCC 下可编译、clang 15 下报错（label at end
   of compound statement、case 后带初始化器声明、C23 `[[fallthrough]]` 等），
   随 `bart/1.0.00` recipe 的同一组精确修复处理。
3. **UNUSED 宏**：BART 1.0.00 从 `misc/misc.h` 删除了 `UNUSED` 宏（0.9.00 及以前
   存在），而 `view.c`/`draw.c` 依赖它 → vendored BART 构建期恢复。
4. **clang blocks**：BART `misc/nested.h` 用 clang blocks 实现嵌套函数，需
   `-fblocks`，链接需 libBlocksRuntime；鸿蒙无该库 → `compat/blocks_runtime_stub.c`
   提供最小 `_Block_*` 符号。
5. **musl 兼容**：`cfl2png.c` 使用 BSD 遗留函数 `rindex()`（musl 未在 `strings.h`
   声明）→ 改为标准等价 `strrchr()`。

## 测试

上游无任何自动化测试（仓库仅 `src/`，`.gitlab-ci.yml` 只跑 `make all`，Makefile
无 `test`/`check` 目标）。适配后新增：

- `test_package/test_cfl2png.py`（**鸿蒙特有测试**）：构造合成 CFL 数据集，运行
  被测 `cfl2png` 端到端导出 PNG（校验签名/IHDR 尺寸/数据依赖/确定性），并校验
  `view` 在无 DISPLAY 下 GTK3 依赖栈完整加载。

详见 `0.3.00/reports/test-report.md` 与 `0.3.00/test_package/MANIFEST.yml`。
