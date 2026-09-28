# cpp_redis 4.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

- git worktree add -b feat/cpp_redis-4.3.1 <wt> origin/main (R01 新建 worktree)
- python3 scripts/ohc-run.py init-build cpp_redis 4.3.1 --url=https://github.com/Cylix/cpp_redis/archive/refs/tags/4.3.1.tar.gz
- tacopie 子模块为空目录：git fetch 上游 commit 243089d84a5a8032b85e81cae237b823df99abee 到 work 的 tacopie/
- cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF
- make -j2 && make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1 拒绝上游 cmake_minimum_required(2.8.7) | CMake ≥3.5 移除 <3.5 兼容 | 配置加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | install 失败: bin 目录不存在 | 静态库构建无 RUNTIME 输出 | CMakeLists install bin 加 if(EXISTS) 守卫 |
| 3 | googletest ExternalProject clone github.com 超时 | github.com:443 不可达 | GIT_REPOSITORY 改 gitee 镜像 + GIT_TAG release-1.10.0 |
| 4 | googletest main 需 C++17，上游测试用 C++11 | 新版 gtest 提高标准 | 固定 googletest release-1.10.0（C++11 兼容） |
| 5 | gmock 编译 -Werror,-Wdeprecated-copy 报错 | clang 15 对该模式升级为 error | ExternalProject CMAKE_CXX_FLAGS=-Wno-error=deprecated-copy |
| 6 | redis_client/subscriber 集成测试需真实 Redis | R01 环境无 redis-server 时未运行 | R03 本机构建并启动真实 redis 8.6.0（127.0.0.1:6379，PING=PONG）后实测 redis_client_spec 26/26、redis_subscriber_spec 29/29 全部通过 |

## 源码修改

- CMakeLists.txt: install bin 目录 if(EXISTS) 守卫；googletest ExternalProject 改 gitee 镜像 + GIT_TAG release-1.10.0 + 策略/编译 flag CMAKE_ARGS

## 依赖版本

- tacopie（内置 submodule，上游 pin commit 243089d84a5a8032b85e81cae237b823df99abee，SHA-256 19a6af00b00a57172907fbf361f8acb7779f3812312a7060fdb52c4badaf4b95）

## 验证结果

```bash
- 8 个纯单元测试全部 PASS：reply(6) array_builder(7) builders_factory(6) bulk_string_builder(9) error_builder(7) integer_builder(10) reply_builder(5) simple_string_builder(7) 共 57/57
- R03 实测：redis_client_spec 26/26 PASS、redis_subscriber_spec 29/29 PASS（真实 redis 8.6.0 服务，127.0.0.1:6379，PING=PONG）；上游 10 个 ctest 入口用例级合计 112/112 PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
- 本库为静态库（libcpp_redis.a + libtacopie.a），无独立打包产物；conan 制品由 conan create 生成于本地缓存

## 注意事项

- tacopie 为 git submodule，发布 tar.gz 不含内容，需按上游 pin commit 引入
## 知识路径判定（knowledge_decision: reuse_existing → 路径 A）
- 候选1 CMake minimum_required<3.5 vs CMake 4.x → E103/E187 等价命中（bump/CMAKE_POLICY_VERSION_MINIMUM）
- 候选2 release tarball 不含 submodule（tacopie）→ E150 等价命中（manual-download）；DRAFT-E616 同族草稿
- 候选3 gmock/gtest -Werror deprecated-copy → E198 等价命中
- 候选4 googletest ExternalProject 网络获取失败 → E342 等价命中（disable-networked / pinned offline dep）
- 候选5 静态库 install 缺失 bin 目录 → 无独立等价条目，属低价值小修，归入 E103/E187 家族，不单独建草稿
- 路径 A 结论：不创建新草稿；命中条目经逐字段适用性验证
---

**编译结束**: 2026-09-27 13:40
**最终状态**: built

## R03 知识路径判定（knowledge_decision: reuse_existing → 路径 A）
- 快照：/storage/Users/currentUser/knowledge-snapshot-cpp_redis-4.3.1-r03-...（ref main, HEAD c611f7d61b422eda200fc49481cf0d404e63f10c, sparse knowledge）
- R01 命中条目复核存在：E103/E187（cmake 版本）、E150（submodule tarball）、E198（deprecated-copy）、E342（测试框架网络获取）
- 本轮新候选：真实 Redis 服务提供（redis 8.6.0 本机构建 + 集成测试）→ E085（musl pthread_cancel，redis 构建依赖）等价；统计口径修正（用例级 112 vs 入口 10）为交付/规则修正，非新增知识条目
- 无新增可沉淀跨库知识 → 路径 A，不创建草稿；未写正式 E###/索引/其他库目录
