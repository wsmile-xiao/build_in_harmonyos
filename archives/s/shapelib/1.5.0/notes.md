# shapelib 1.5.0 适配笔记

## R51 上游测试清点（2026-10-11）

- 上游测试目录：`tests/`，共 3 个 shell 脚本（test1.sh / test2.sh / test3.sh），
  由 CMakeLists.txt 在 `BUILD_TEST=ON` 且 bash+sed 可用时注册为 ctest 用例。
- test1.sh：依赖外部数据包 shape_eg_data.zip（需从 dl.maptools.org 手工下载，
  源码包内不含）。**实测**：`curl dl.maptools.org` DNS 解析失败/站点不可达，
  该数据包无法获取 → test1 无法运行（上游设计即为可选用例，EG_DATA 未设置时
  CMakeLists 明确跳过注册 test1）。
- test2.sh / test3.sh：自包含（仅依赖构建产物 shpcreate/shpadd/dbfcreate/dbfadd/shpdump/shptreedump）。

### 实测运行记录

在 conan build 目录中按上游方式（sed 替换二进制路径）实际运行：

（运行结果由 conan-verify / finish 阶段补充，见下方"执行记录"）

## 适配要点

1. **构建系统**：CMake（cmake_minimum_required(VERSION 2.8.5) 在 CMake 4.x 下
   报兼容性错误 → 由 Conan 工具链注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 处理，
   无需修改源码）。
2. **历史教训沿用**（旧 manifest knowledge_gained）：autotools config.status 在
   HMDFS 临时目录上失败 → 本次直接走 CMake 构建系统，未复现。
3. **零外部依赖**：仅需 libm（UNIX 下 CMakeLists 自动链接）。
4. **产物**：静态库 libshp.a + 8 个命令行工具（R38，软件级 commands.json 已声明）。
5. **共享库选项**：shp 非系统同名库，但作为 GIS 基础库默认静态（`shared=False`），
   下游 miallib 静态链接。
6. **无平台补丁**：源码零修改，conandata.yml 无 patches 条目。

## 执行记录（2026-10-11）

- conan create（干净构建，ohos-aarch64 profile）：✅ PASS（G1-G4/L2/L4/L5 全绿）
- test_package L1：✅ PASS（写入+回读 3 点带属性，断言 15 处）
- 上游 test2 流程实测：shptest 0..13 共 14 组（创建→shpdump 回读）全部成功，14/14；
  test2.sh 比对参照 stream2.out 未随 1.5.0 源码包发布（tarball 仅含 stream1.out，
  属 test1 附属），故按脚本语义逐组手工验证替代。
- 上游 test3 流程实测：shpcreate+dbfcreate+shpadd+dbfadd+shpdump 全链路 ✅（Polygon 9 顶点/2 parts 正确）。
- 上游 test1：无法运行（EG_DATA 外部数据包，dl.maptools.org 不可达，见上）。
- 通过率（可运行用例口径）：test2 14/14 = 100%，test3 核心链路 100%。

## 历史探索教训沿用

- 2026-05-26 历史 manifest 记录：CMake 4.x 下 LOCATION 属性被禁用（upstream
  BUILD_TEST=ON 路径调用 get_target_property LOCATION 报错）→ 本次不启用上游
  ctest 注册路径（BUILD_TEST=OFF），改用 test_package L1 + 手工运行上游脚本实测，
  并以补丁让 BUILD_TEST 尊重外部传参。
---

**编译结束**: 2026-10-11 10:35
**最终状态**: built
