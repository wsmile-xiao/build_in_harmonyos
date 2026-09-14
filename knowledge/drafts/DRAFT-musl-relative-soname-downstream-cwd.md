# DRAFT-musl-relative-soname-downstream-cwd: musl 相对 soname 下游消费陷阱

> **Contributor**: j669539 | **Status**: Draft | **Updated**: 2026-09-06
> **Source**: kcalendarcore 6.26.0 适配（PR #8667，分支 feat/kcalendarcore-6.26.0）
> **拟提升编号：由知识库主编确认（建议 E607）**

## 问题
kcalendarcore 6.26.0 全新适配，W3 首轮 CTest 505/505 全挂，统一报"加载不到 ./libical.so"；conanrun 的 LD_LIBRARY_PATH 无效。perl runner 数据驱动测试与单元测试同一加载错误无差别全挂——系统性环境问题。

## 根因（四步因果）
1. libical/4.0.1 制品为过 L5 SONAME 门禁打 relative-soname 补丁（-Wl,-soname,./）
2. 下游 DT_NEEDED 变为含 "/" 的相对路径 ./libical.so
3. musl 对含 "/" 的 DT_NEEDED 按进程 CWD 解析、不查 LD_LIBRARY_PATH（glibc 差异）
4. CTest 进程 CWD=build/Release（--test-dir），该目录无 libical*.so

## 定位三步法
readelf -d 查 SONAME/DT_NEEDED → 对照 libical 配方 _prepare_ctest_runtime_links（自家测试也拷 .so 佐证）→ cp .so 到 CWD 实验（挂变过实锤）

## 修复
配方 test 环节拷 libical 4 个 .so 到 build/Release 与 build/bin（HMDFS 用 rm -f && ln -s）。传递性警告：KF6CalendarCore.so 自身 DT_NEEDED=./libical.so，二级下游连环踩坑。预防：W0 readelf 查依赖制品 SONAME 遇相对路径提前注入拷贝步骤。

## 验证
修复前 505/505 全挂 → 修复后 505/505 全数真实运行通过 + test_package 通过 + CI 绿 + review 清零。
