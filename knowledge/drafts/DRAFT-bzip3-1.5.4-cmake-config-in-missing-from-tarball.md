# CMake release tarball 打包遗漏被引用的模板文件导致 configure_file 失败

- **草稿 ID**: DRAFT-bzip3-1.5.4-cmake-config-in-missing-from-tarball
- **来源**: bzip3 1.5.4 HarmonyOS PC 适配（release tarball 缺失 bzip3-config.cmake.in）
- **分类**: cmake / packaging / source-download
- **状态**: 本地草稿（路径 B 知识库扩展，随 bzip3 1.5.4 归档 PR 交付）

## 问题 / 错误签名

- **cmake configure 失败**：
  ```
  CMake Error: File /storage/Users/currentUser/tmp/builds/bzip3-1.5.4.work/bzip3-config.cmake.in does not exist.
  CMake Error at CMakeLists.txt:102 (configure_file):
    configure_file Problem configuring file
  ```
- **复现命令**: `cmake -B build ...`（任意配置参数均触发，因 CMakeLists.txt 无条件 configure_file 该文件）
- **退出码**: 1

## 根因

上游 1.5.4 release tarball 打包时遗漏了 `bzip3-config.cmake.in`——CMakeLists.txt 第 102 行
`configure_file(... bzip3-config.cmake.in ...)` 必须读取该文件，缺失即配置直接失败。
上游 git tag 1.5.4 实际存在该文件（`curl https://raw.githubusercontent.com/iczelia/bzip3/1.5.4/bzip3-config.cmake.in`
可取得），属上游打包流程缺陷，与 HarmonyOS 平台无关。

## 最小修复方案

1. 确认上游 git tag 存在该文件（官方 raw URL 拉取验证）。
2. 在 `patches/` 下创建新增文件补丁，内容与上游 git tag 完全一致：
   ```cmake
   if(@BZIP3_ENABLE_PTHREAD@)
     include(CMakeFindDependencyMacro)
     find_dependency(Threads)
   endif()
   include("${CMAKE_CURRENT_LIST_DIR}/bzip3-targets.cmake")
   ```
3. `conandata.yml` patches 段注册该补丁。
4. 重跑 `cmake configure` / `conan create` 复验。

## 验证结果

- cmake configure → `Configuring done / Generating done`（退出码 0）
- conan create → G2 PASS
- build_and_test.sh → L0/L1/L2/L5 全 pass（100%）

## 适用边界

- 适用：CMake 项目 release tarball 打包遗漏被 CMakeLists.txt 引用的模板/配置文件，且上游 git tag 存在该文件。
- 反例：若上游 git 也不存在该文件，需自行生成并评估消费者影响，不属本条目。

## 查重差异（与既有条目）

- 与 E150（release tarball 不含 submodule 内容）仅触发面部分重叠（release tarball 不完整），根因（submodule vs 单文件模板遗漏）与方案（git clone 全仓 vs 单文件补丁还原）均不同。
- 新增差异：CMakeLists 引用的模板文件缺失时 configure_file 立即失败 + 从 git tag 还原单文件的补丁方案。similar_to: E150 | caused_by: 上游打包流程遗漏 | conflicts_with: 无。
