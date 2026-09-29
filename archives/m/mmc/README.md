# mmc — Mesh-based Monte Carlo (MMC)

基于四面体网格的 3D 光子输运蒙特卡洛模拟器（Mesh-based Monte Carlo），用于生物医学光子学中的
光在复杂组织中的传播建模。命令行工具 `mmc` 读取 `.inp`/`.json` 输入文件与 FEM 网格文件
（`node_<id>.dat` / `elem_<id>.dat` / `facenb_<id>.dat` / `velem_<id>.dat` / `prop_<id>.dat`），
执行光子输运仿真并输出通量（flux）等结果。

- 上游：<https://github.com/fangq/mmc>（tag `v1.0` = "MMC 1.0 Final (v2018 - Sachima)"，2018-08-26）
- 许可：GPL-3.0-or-later
- 官网：<http://mcx.space/mmc>

## 版本

| 版本 | 构建系统 | 状态 | 说明 |
|------|----------|------|------|
| 1.0  | make     | built | 上游 tag `v1.0`；aarch64/OHOS 适配（clang + musl） |

## 构建

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方使用上游 README 记录的 `make release` 目标（`-O3`，无 SSE/OpenMP），并以
`-fPIC` 之外不引入额外依赖；`sse`/`ssemath` 为 x86 专属，`omp` 会把构建机 RUNPATH 烤进产物，
均不采用。

## 包内容

```
bin/mmc            # 命令行可执行文件（ELF64 AArch64）
licenses/LICENSE.txt
```

## 使用

```bash
mmc                       # 打印 banner 与参数说明
mmc -f case.inp -s out -n 1000000 -b 1 -D TP   # 运行案例
```

参数、输入文件格式与全部构型（生成网格的 `matlab/` 辅助函数、`mmclab` MATLAB/Octave 绑定等）
见上游 `README.txt` 与 <http://mcx.space/mmc>。
