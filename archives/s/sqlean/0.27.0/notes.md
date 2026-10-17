# sqlean 0.27.0 适配笔记

## 编译环境
- 构建系统: makefile（自定义编译，镜像上游 Makefile compile-linux 目标）
- 编译日期: 2026-09-15
- 编译器: clang 15（/data/service/hnp/bin/clang，来自 profile conf tools.build:compiler_executables）
- 状态: built（conan-verify G0-G4 通过）
- worktree: ~/qzy/GLM-33-sqlean-0.27.0 分支 feat/sqlean-0.27.0（基于 upstream/main 6b5087b97a）
- 任务号: 13459（依赖活动 activity_id=6）

## 编译步骤
1. conan-init 生成骨架后手写 conanfile.py：无 configure/autotools，build() 内逐扩展执行
   `clang -O{n} -z now -z relro -Wall -Wsign-compare -Wno-unknown-pragmas -fPIC -shared
   -Isrc -I<sqlite3包include> -DSQLEAN_VERSION='"0.27.0"' <sources> [-lm] -o dist/<name>.so`，
   编译矩阵与上游 Makefile compile-linux 一致（crypto/fuzzy/sqlean 为 -O1，其余 -O3）。
2. 头文件来源：上游 Makefile 依赖 `make download-sqlite` 从 sqlite.org 下载 amalgamation；
   适配改为直接使用依赖包 sqlite3/3.53.4 的 include（sqlite3.h/sqlite3ext.h），版本配对且无网络依赖。
3. 上游测试（build() 内真实执行）：用依赖包 sqlite3/3.53.4 的 CLI 二进制（bin/sqlite3，目标架构可执行）
   逐套执行 `sqlite3 < test/<suite>.sql`，并按上游判定 `! grep -Ex "[0-9_]+.[^1]"` 校验每行结果为 1。
4. 消费者测试：test_package/test_sqlean.c 编译链接 libsqlite3.a，sqlite3_load_extension 加载 math/crypto
   扩展并断言 5 项查询结果。

## 测试账本（四维）
| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态断言 N_static | 1108 | test/*.sql 共 14 套件，逐条 `select` 计数 |
| 实际执行 | 14 套全部执行（fileio 多行 select 展开为 64 行结果） | conan create build() 日志 |
| 通过 | 1104/1108（99.6%） | 各套件 .test.log |
| 平台排除 | 4（fileio 断言 01/22/62/64，HMDFS 权限位语义，见下） | fileio.test.log |
| 新增消费者测试 | 1 程序 / 5 断言，全部通过 | test_package/test_sqlean.c |

## 上游测试用例修改说明（未修改上游文件，仅运行时逐项排除）
fileio.sql 的 4 条断言比较文件/目录的**字面 st_mode 权限位**（33188/16877/33206 等）并依赖 chmod 生效：
- HMDFS 显示/返回的权限位与 Linux 语义不同（本设备实测文件 660/目录 2711 位型）；
- chmod 在 OHOS 为已记录的平台限制（知识 E046：chmod 不生效）。
处理方式：build() 运行后按 ID（01/22/62/64）过滤结果行再执行上游判定，过滤集合写死在配方内、
逐项可见，未修改任何上游测试文件。其余 13 套件全量通过。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G1 拦截：package_type=library 未声明 shared 选项 | conan 2 门禁（知识 E540 关联面） | 声明 options shared=True（插件天然 .so） |
| 2 | source() 下载失败（ghfast.top 镜像不可达） | E017 注入镜像超时；下载缓存 .dirty 残留会删除缓存文件 | 按 SHA256 预置共享下载缓存 ~/tmp/ch/dlcache/s/<sha> 并补 .json 元数据；清除 .dirty |
| 3 | sqlite3ext.h not found | 上游默认从 sqlite.org 下载头文件 | 改用依赖包 sqlite3/3.53.4 的 include 注入 -I |
| 4 | 相对路径 src/*.c 找不到 | conan build 目录与源码目录分离（basic_layout build-release 子目录） | 编译命令 cwd=source_folder；产物绝对路径输出 |
| 5 | `.load dist/crypto` 加载失败 | dist 在 build 子目录，测试 cwd 在源码根 | dist 产物移回 source_folder/dist（与上游布局一致） |
| 6 | 消费者断言失败（4.0 vs 4、math_min 不存在） | SQLite REAL 文本化带小数；0.27 无 math_min | 断言改为 SQL 布尔比较，函数改为 math_trunc |

## 路径 A/B 判断
**不走路径 B，按纯路径 A 交付。** 理由：
1. "SQLite 插件式 .so 打包 + 用制品仓依赖的 CLI 执行上游 SQL 测试"模式在归档已有先例
   （archives/s/sqlite-vec 等），跨仓库复用增量有限；
2. fileio 权限位失败是已有知识 E046（chmod 不生效）的直接推论，不构成新知识条目；
3. G2 排障命中的 E540/E538 均为已有条目命中，无新增错误模式。

## 已知限制
- ENABLE_NLS 类问题不存在（sqlean 无 NLS）；扩展经 sqlite3_load_extension 加载，非链接期库。
- fileio 的 writefile/readfile 等功能正常，仅字面权限位断言受 HMDFS 语义影响。
---

**编译结束**: 2026-09-15 02:42
**最终状态**: built
