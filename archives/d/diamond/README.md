# diamond

DIAMOND — 与 BLAST 兼容的蛋白质序列本地比对工具。高性能序列比对器，支持蛋白质搜索和翻译 DNA 搜索，专为大规模基因组数据的快速分析而设计。速度远超 BLAST，灵敏度与之相当。

- **主页**: https://github.com/bbuchfink/diamond
- **许可证**: GPL-3.0-or-later
- **编程语言**: C/C++

## 可用版本

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| 2.1.24 | built | cmake | HarmonyOS 上需 AARCH64=ON + X86=OFF |

## 2.1.24 版本说明

### 依赖
- sqlite3（3.49.1 或兼容版本）
- zlib（1.3.1 或兼容版本）

### 构建配置（HarmonyOS aarch64）
在 aarch64/HarmonyOS 上，以下 CMake 选项**必须设置**：
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
          -DCMAKE_BUILD_TYPE=Release \
          -DAARCH64=ON \
          -DX86=OFF
```

**为何需要 AARCH64=ON + X86=OFF**：不设置这些标志时，diamond 会尝试编译 x86 SSE4.1/AVX2 SIMD 目标，在 aarch64 上因未知类型 `__m256i`、`__m128i` 而失败。设置 AARCH64=ON 会启用 NEON SIMD 目标代替。

**为何不能设置 CMAKE_SYSTEM_NAME=Linux**：设置 `CMAKE_SYSTEM_NAME=Linux` 会触发 CMake 的交叉编译模式，绕过 diamond 对平台架构的自动检测。在本机 aarch64 编译时，不应设置此标志。

### 内置测试
diamond 包含完整的回归测试套：
```bash
diamond test
# 输出: 20 个 blastp 测试 + 2 个压力测试 = 22/22 通过
```

### 已验证的子命令
- `makedb` — 从 FASTA 文件构建 DIAMOND 数据库
- `blastp` — 蛋白质对蛋白质比对（支持表格、XML、PAF、配对格式）
- `blastx` — DNA 对蛋白质比对
- `dbinfo` — 数据库元数据查看
- `getseq` — 从数据库检索序列
- `cluster/linclust` — 蛋白质聚类