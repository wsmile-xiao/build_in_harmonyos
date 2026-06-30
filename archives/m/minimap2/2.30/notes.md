# minimap2 2.30 适配笔记

## 编译信息
- 构建系统: Makefile (非 autotools)
- 平台: aarch64 (ARM64)
- 编译器: clang 15.0.4
- 编译参数: `make arm_neon=1 aarch64=1 CC=clang AR=llvm-ar CFLAGS="-fPIC -O2 -g -Wall -Wc++-compat -D_FILE_OFFSET_BITS=64 -fsigned-char"`

## 编译过程

### 构建适配
1. minimap2 是纯 Makefile 项目，没有 configure 脚本，不需要 `./configure` 步骤
2. 在 aarch64 平台上需要用 `arm_neon=1 aarch64=1` 参数启用 NEON SIMD 支持
3. NEON 代码路径使用 sse2neon 头文件实现 SSE2→NEON 翻译
4. 编译产生: minimap2 二进制 + libminimap2.a 静态库

### 安装适配
- Makefile 没有 install 目标，需要手动安装
- 手动安装: minimap2 → bin/, libminimap2.a → lib/, minimap.h/mmpriv.h → include/, minimap2.1 → share/man/man1/

### 测试结果
- `minimap2 --version` → 2.30-r1287 ✅
- 比对功能测试 (-Pa, -x asm5, -x map-pb) → 全部通过 ✅
- NEON SIMD 代码路径 → 正确工作 ✅

---

**编译开始**: 2026-05-25
**编译结束**: 2026-05-25
**最终状态**: published
**编译耗时**: 约 5 分钟
