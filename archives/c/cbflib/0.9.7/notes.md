# cbflib 0.9.7 OHOS 适配笔记

- 适配日期: 2026-09-05（HarmonyOS PC 设备单端）
- 分支: `feat/cbflib-0.9.7`（基于 upstream/main `ad28aeca82`）
- 上游: https://github.com/yayahjb/cbflib （tag `CBFlib-0.9.7`，Debian watch 反查权威上游；sourceforge 项目同步发布）
- 源码: `CBFlib-0.9.7.tar.gz`，SHA-256 `e4acf8f7b5cc4e788215983ff428c2f8aa1fdbbfc6d163ace7999dcd2a10b19f`
  - init-build/search-url 曾给出 `waterlan.home.xs4all.nl` 镜像 URL，实测为 12KB HTML 停放页（magic `3c21`），按流程判不可用；`[Official]` 标注为假阳性
- 工具链: 设备 clang 15.0.4（aarch64-unknown-linux-ohos）、GNU Make 4.4.1、Python 3.12.8、Conan 2.29.1

## 构建系统要点

上游是 m4 生成的多平台 Makefile（无 configure）。关键接线：

- `include/cbf_hdf5.h` 无条件 `#include <hdf5.h>` → libcbf 核心硬依赖 HDF5；
  传 `HDF5_PREFIX=<hdf5 包前缀>` 启用系统 HDF5 分支（`CBFLIB_DONT_USE_LOCAL_HDF5`），
  上游自动补 `-DH5_USE_110_API` 与 `-lhdf5 -lz -ldl` 链接（HDF5LIBS_SYSTEM）。
- `REGEX_PREFIX=<pcre 包前缀>` → `CBFLIB_DONT_USE_LOCAL_REGEX=yes`（禁 pcre-8.38 下载），
  `REGEX_LIBS="-L<pcre lib> -lpcreposix -lpcre"`；pcre/8.45 提供 `pcreposix.h` + `libpcreposix.a`。
- `NOFORTRAN=1` 跳过 libfcb（OHOS 无 Fortran 工具链，上游合法开关）。
- `CBFLIB_DONT_USE_LZ4/BSHUF/PY2CIFRW/PY3CIFRW=yes` 跳过可选捆绑组件的构建期下载。
- `CBFLIB_DONT_USE_TIFF=yes`（本 PR 新增，上游风格开关）：ohpcd 无 tiff 发布（conan list = 0），
  跳过 tiff2cbf 工具及其测试组；全树无 `__OHOS__` 式条件编译（R8）。
- make 变量 `C++` 无法用命令行覆盖（`C++=x` 被解析为变量 `C+` 追加）→ 补丁将 default 段改为
  `C++ ?= g++` 后用 `env 'C++=<clang++>' make` 传入（知识草稿 E547）。
- Makefile 有 `Makefile: m4/Makefile.m4` 再生规则 → 补丁同时改 m4 模板与再生产物，
  `build()` 用 `os.utime` 钉同一时间戳（知识草稿 E549）。

## 依赖（W0 实证）

- hdf5/1.14.6（ohpcd，`--build=never` 真实下载安装 ✓）
- pcre/8.45（ohpcd，`--build=never` ✓；提供 pcreposix）
- zlib/1.3.1.1 + libaec/1.1.7（hdf5 传递依赖，同样实证 ✓）

## 上游测试（设备原生，同一源码+补丁）

统计单位 = 测试动作（1 次工具执行或 1 个比较断言）。取数命令：
`make -j1 basic`、`make -j1 extra dectristests`，与日志 `test-basic-2.log`/`test-extra-3.log` 运行行核对。

| 目标 | TOTAL | PASS | FAIL | SKIP | NOT_RUN |
| --- | --- | --- | --- | --- | --- |
| basic | 11 | 11 | 0 | 0 | 0 |
| extra | 71 | 58 | 0 | 4 | 9 |
| dectristests | 2 | 2 | 0 | 0 | 0 |
| 合计 | 84 | 71 | 0 | 4 | 9 |

- SKIP(4)：XRD1621 tiff 往返组（tiff2cbf 执行 + 1 比较 + cif2cbf 执行 + 1 比较）——OHOS 无已发布 tiff 包。
- NOT_RUN(9)：6 个 h5dump 执行 + 3 个 dump 比较——conan hdf5 包不含 h5dump 工具；上游该组为 `-` 前缀非致命断言；对应的 cif2cbf 六路 HDF5 转换（opaque/encI/encp/encb/encc/encz）与回读比较全部 PASS。
- 上游默认不编译/不在范围（不计入 TOTAL）：Fortran 组（NOFORTRAN 下 Makefile 不含，无 flang/gfortran）、testulp（CBF_USE_ULP 默认关）、py2cbftests/py3cbftests（SWIG 未装且绑定不在 C 库包范围）。

## 数据文件

上游测试数据 `CBFlib_0.9.7_Data_Files_Input/Output.tar.gz`（sourceforge，38MB/85MB）仅用于设备原生测试，
不进入 conandata（CI 体积与时延不可控）；test_package 使用自建消费者（公开 API 往返）。

## 测试包

`test_package/consumer.c`：cbf_make_handle → 构造 datablock/category/column → 写二进制 CBF →
回读校验文本值 + 8x6 packed int 数组逐元素一致 → 真实 L2 消费者。
