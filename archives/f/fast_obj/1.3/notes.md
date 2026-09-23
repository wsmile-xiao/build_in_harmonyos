# fast_obj 1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 (OHOS SDK, -pr:h=ci/conan/profiles/ohos-aarch64)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build fast_obj 1.3 --url https://github.com/thisistherk/fast_obj/archive/refs/tags/v1.3.tar.gz`
2. `ohc-run.py conan-init fast_obj 1.3` 生成 conanfile.py + conandata.yml + test_package/
3. `ohc-run.py conan-verify fast_obj 1.3`（G1-G4/L2/L4/L5 全通过）
4. `ohc-run.py finish fast_obj 1.3 built`（含 W3 本地 CI 模拟，通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 conan create 失败：`Compatibility with CMake < 3.5 has been removed` | 上游 CMakeLists.txt 首行 `CMAKE_MINIMUM_REQUIRED(VERSION 3.0)`，OHOS 工具链 CMake 4.1.2 拒绝 <3.5 的 policy | conanfile.py generate() 用 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（**必须 cache_variables**：tc.variables 写入 toolchain 文件，在 cmake_minimum_required 之后加载不生效；cache_variables 走 -D 命令行在任何 CMakeLists 解析前生效） |
| 2 | 上游 CMakeLists.txt 无 install() 规则 | 上游只定义 INTERFACE `fast_obj` + STATIC `fast_obj_lib`，不提供安装目标 | package() 手工 copy：fast_obj.h → include/、LICENSE → licenses/、libfast_obj_lib.a → lib/；package_info().cpp_info.libs=["fast_obj_lib"] |
| 3 | W3 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | 另一库 util-linux-login 基线含未登记隐藏文件（tracked 空文件，commit 761df452e5），本分支尚无 commit 时 junk_check 走 full 模式（git ls-files）全仓扫描 | 按基线隔离规则：临时 `git rm --cached` 该精确路径 → 复验 W3 通过 → 无条件恢复（`git restore --staged --source=HEAD`，blob/sha256 与 HEAD 完全一致），隔离期间未提交、未改他库 |
| 4 | test_package 首跑断言失败 `position_count=9, expected 8` | fast_obj 的 position 数组下标 1-based（索引 0 是缺失数据哨兵），8 顶点 → position_count=9 | test.c 断言改为 9，并注释说明 1-based 语义 |

## 源码修改

无补丁。上游源码零修改；适配全部在 conanfile.py 的 generate()/package() 中完成（CMAKE_POLICY_VERSION_MINIMUM 注入 + 手工制品收集）。

## 依赖版本

无第三方依赖（纯 C 单文件库，仅 C 标准库）。

## 验证结果

```bash
conan create archives/f/fast_obj/1.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# G2 PASS（库构建 + test_package 消费者测试通过）
```

- 消费者测试：test_package/test.c 解析 cube.obj，断言 position_count=9 / face_count=6 / group_count=1，通过
- 上游测试：上游 test/test.cpp 需外部 .obj 文件入参且依赖 tiny_obj_loader.h，未纳入 conan build（已声明于 MANIFEST.yml）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x 配方（CMake，cache_variables policy 注入，手工打包） |
| conandata.yml | 官方源码 URL + sha256=f0f175edbe60db2099b3d8266ff0085b21862a17d9a1dc00fd195258c5b622b1 |
| test_package/ | L1 消费者测试（test.c + cube.obj + MANIFEST.yml） |
| manifest.yaml | 版本级元数据（build_system=cmake, status=built） |

## 知识查重结论（executor_local 官方快照）

- 快照: /storage/Users/currentUser/runnerljs002/knowledge-snapshots/fast_obj-1.3-<task_id>
  repository=https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git, ref=main, HEAD=dfe3d3ac77fa, sparse=knowledge, read-only
- 扫描范围: knowledge/graph/E*.kv + knowledge/doc/E*.md + knowledge/drafts/*.{md,kv} 全覆盖
- 候选: G2 首错 "Compatibility with CMake < 3.5 has been removed"（上游 CMakeLists.txt `CMAKE_MINIMUM_REQUIRED(VERSION 3.0)` vs OHOS CMake 4.1.2）
- 等价命中: DRAFT-E321-cmake4-policy-version-minimum.kv（error_signature `Compatibility with CMake < 3\.5 has been removed` 逐字段命中；
  root_cause=CMake 4.x 移除 <3.5 兼容；approach=cache_variables 设 CMAKE_POLICY_VERSION_MINIMUM=3.5 且明确"切勿用 tc.variables" —— 本次实测一致：
  先以 tc.variables 注入失败，改 cache_variables 后通过）+ E321-draft-220E.kv（无 install() 规则时显式制品收集，与 fast_obj 上游无 install() 一致）
- knowledge_decision: reuse_existing → 路径 A（【积分赛】PR-only），本轮不创建任何知识草稿
- 无其他可沉淀的跨库经验（无 install() 打包、position 1-based 哨兵条目均为库自身行为，记于本 notes 即可）

## 注意事项

- 上游 CMakeLists.txt 的 `FAST_OBJ_BUILD_TEST` 选项默认 OFF（测试程序需外部 .obj 参数），配方维持 OFF，消费者覆盖在 test_package
- position/texcoord/normal 数组均为 1-based（索引 0 为哨兵），消费者直接索引下标 0 会得到哨兵值