# xlsxio 0.2.36 适配笔记

## 任务来源

- 平台任务 contrib-12139（开源鸿蒙PC专项积分赛），分支 `feat/xlsxio-0.2.36`，2026-09-18 认领
- 上游：https://github.com/brechtsanders/xlsxio （524 stars，非 fork，tag 0.2.36 实拉核验存在）
- 语言实测（R47 lang-preflight）：C（源文件 14 个全为 .c，CMakeLists `PROJECT(xlsxio ... "C libraries ...")`）

## 选库核验（§3.2 否决线）

1. 他人已移植：`archives/` 全量比对 + `git grep xlsxio` 同源反查均无；制品仓 `conan list "xlsxio/*" -r=ohpcd` = 0（设备实测）
2. 语言/构建生态：C + CMake，CI 工具链具备
3. 难度定级：A（纯编译适配，零补丁）——依赖 libzip/1.11.4、expat/2.8.2 均已发布制品仓（W0 设备侧实测）

## 上游测试清点（R51）

- 上游**无测试套件**：CMakeLists.txt 无 `add_test`/`enable_testing`、无 tests/ 目录；`examples/` 下 5 个程序（example_xlsxio_write/read 等）为演示代码，无断言
- 证据命令：`grep -rn "add_test\|enable_testing" xlsxio-0.2.36/` → 0 命中
- 因此申报：上游测试 0 项；验证全部由 test_package 承担（库级 14 项断言 + CLI 4 项断言）

## 平台适配要点

- **CMake 4.x 兼容**：上游 `CMAKE_MINIMUM_REQUIRED(2.6)` 被 CMake 4.x 拒绝（<3.5 兼容已移除）。配方传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4 官方机制），无补丁
- **依赖定位**：`LIBZIP_DIR`/`EXPAT_DIR` 指向 conan 包目录，走 CMakeLists 自带的 `NO_DEFAULT_PATH` 分支，规避系统库污染
- **LD_LIBRARY_PATH 盾**：build() 与 test_package 均显式清空（lld/libxml2 根因，同 libodfgen/libabw）
- **zip 后端选型**：`WITH_LIBZIP=ON`——minizip-ng 有档案但未发布制品仓（"有档案无发布"），libzip 已发布，直接用已就绪依赖

## 交付形态

- 库：`libxlsxio_read` + `libxlsxio_write`（默认静态，shared 选项可用）
- 工具：`xlsxio_xlsx2csv`、`xlsxio_csv2xlsx`（包级 commands.json 已声明，R38）

## 编译结束

设备实机验证（2026-09-18，OHOS aarch64）：

- `conan-verify`：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（RC=0）；test_package 库级 16 项断言全过（failed=0），CLI 回环 4 值全保留
- CI 同源闸门 `CI_PACKAGES=archives/x/xlsxio/0.2.36 zsh ci/conan/build_and_test.sh`：L0/L1/L4/L5 全 pass，Pass rate 100%，RC=0
- 产物：静态库 libxlsxio_read.a/libxlsxio_write.a + 头文件 + CLI 工具 xlsxio_xlsx2csv/xlsxio_csv2xlsx

踩坑记录（已修复）：

1. `CMAKE_POLICY_VERSION_MINIMUM` 必须走 `tc.cache_variables`——上游 `cmake_minimum_required` 在第 1 行，先于 toolchain 文件求值；且 3.5 基线下 CMP0077=OLD，option() 会覆盖 toolchain 普通变量，所有开关都得用 cache_variables
2. FindLibZip.cmake 缺 `INCLUDE(FindPackageHandleStandardArgs)`（旧 CMake 靠 FindZLIB 间接加载；zlib 不在查找路径时新版 CMake 直接报错）→ patches/0001
3. xlsxio_xlsx2csv 按工作表导出为 `<xlsx>.<sheet>.csv`，不是 `<xlsx>.csv`
