# CDO (Climate Data Operators)

**气候数据算子集合** —— 处理气候与数值天气预报（NWP）模式数据的命令行工具，
提供 700+ 算子：NetCDF/GRIB 读写与格式转换、统计与时间序列运算、插值、
重网格（含保守重映射）、垂直插值、EOF/谱分析等。

- 上游：https://code.mpimet.mpg.de/projects/cdo
- 许可证：BSD-3-Clause

## 用法

```bash
cdo -V                        # 版本
cdo -h                        # 算子列表
cdo sinfo in.nc               # 查看文件信息
cdo -f nc -random,r10x5 a.nc  # 生成随机场
cdo add a.nc b.nc sum.nc      # 逐格点相加
cdo -f grb2 -random,r5x5 g.grb2   # 写 GRIB2（eccodes）
cdo -topo,global_5 topo.nc    # 地形数据（proj）
```

常用环境变量：`CDO_PATH`（算子插件路径）、`ECCODES_DEFINITION_PATH`（GRIB 定义表）。

## HarmonyOS PC 适配（aarch64-linux-ohos）

- 配方：`archives/c/cdo/2.6.3/conanfile.py`（autotools），依赖全部来自制品仓已发布包。
- 平台相关补丁 6 个，集中在 **libc++ 15 的 C++20 ranges 能力**、**musl 缺少 glibc 扩展**、
  **clang 15 的 C++20 语言特性缺口**、**autotools config.guess 的 HarmonyOS 识别** 四类，详见 `2.6.3/notes.md`。
- 交付物：`bin/cdo`（aarch64 ELF，动态链接 musl/libc++_shared）。
- 上游测试（`test/pytest` 112 条 Python 用例 + 1042 个金标准文件）由赛事 CI / 鸿蒙电脑执行
  （WSL 交叉编译环境无法运行 aarch64 产物）。
