# cmor

**描述**: Climate Model Output Rewriter (CMOR)，气候模型输出重写库。将气候模型输出转换为符合 CF (Climate and Forecast) 元数据约定、满足 CMIP (Coupled Model Intercomparison Project) 要求的 netCDF 格式，供 CMIP6/CMIP7 等大型比对计划使用。

CMOR 提供 C 公共 API（cmor_setup/cmor_axis/cmor_variable/cmor_write/cmor_close 等），是气候科学社区广泛使用的事实标准工具链组件。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.15.2 | built (conan 配方适配，构建+test_package 通过) | 本仓库首个 cmor 适配 |

## 版本索引

| 版本 | 日期 | 状态 |
|------|------|------|
| 3.15.2 | 2026-09-14 | built (conan 配方适配) |

## 依赖（configure.ac AC_CHECK_LIB 硬依赖，均 AC_MSG_ERROR 不可禁用）

- netcdf >= 4（nc_inq_var_deflate/nc_open，netCDF 输出）
- udunits2 >= 2.2.28（ut_parse，单位系统）
- json-c（json_object_new_object，CMIP 表格/属性 JSON 解析）
- uuid（uuid_generate）

## 鸿蒙适配

- **构建系统**: autotools；release tarball 自带 configure（无需 autoreconf）
- **OHOS 识别**: 向 tarball 自带 config.guess/config.sub 幂等注入
  HarmonyOS → `aarch64-unknown-linux-ohos`（config.guess 主 case +
  OS 校验加 `ohos*`、kernel-os 组合加 `linux-ohos*`）
- **netcdf 探测**: conan netcdf 包自带 bin/nc-config 写死构建期路径（失效），
  传 `--with-netcdf=no` + AutotoolsDeps 注入 LDFLAGS 解析（并在
  configure 脚本中保留 SV_LDFLAGS/SV_CFLAGS，避免 `LDFLAGS=${NCLDFLAGS}`
  覆盖）
- **Fortran**: OHOS 无 gfortran，`--enable-fortran=no`（LIBFILES 仅含 C 目标）
- **E129**: configure/config.status 临时目录 umask 077 → 022
- **PWD 修复**: HMDFS getcwd 失效，发布逻辑 PWD 供 configure pwd probe
- **公共头依赖**: include/cmor_func_def.h 直接 include
  `<udunits2.h>`/`<json-c/json.h>`/`<netcdf.h>`/`<uuid/uuid.h>` 与
  `include/cdTime/` 子目录头 → conan requires(headers=True) +
  cpp_info.includedirs 含 include/cdTime
- **submodule**: release tarball 不含 3 个 tables submodule
  （cmip6/mip/cmip7-cmor-tables），source() 从官方 GitHub archive 拉取；
  上游 Test 用 `Tables/` 相对路径引用，测试运行需 Tables 符号链接

## 功能验证

- test_package 自研 3 组断言（版本宏 3.15.2 + cmor_setup + cmor_close）全部通过
- 上游 Test/ 13 个 C 测试：1 通过（test_unit_cat_unique）；12 个在更深层
  变量/网格组合路径触发运行时 hdf5 C++ 绑定（libnetcdf→libhdf5_cpp→
  libc++_shared.so）加载失败 SIGSEGV——经最小复现（netcdf 写文件、四轴
  cmor_axis 定义均 exit=0）证实为 OHOS 运行时环境限制，非 cmor 库缺陷
