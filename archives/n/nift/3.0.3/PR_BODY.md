- **三方库名称**：nift（aka nifty-site-manager / nsm，静态网站生成器）
- **上游版本**：3.0.3
- **上游仓库地址**：https://github.com/nifty-site-manager/nsm （官方 tag 源码包：https://github.com/nifty-site-manager/nsm/archive/refs/tags/v3.0.3.tar.gz）
- **适配路径**：路径 A（基础适配，无补丁）
- **使用知识库**：无（纯 Makefile 自包含项目，编译要点基于探索实测并沉淀至 manifest.yaml knowledge_gained / notes.md）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游无测试框架（官方 tag v3.0.3 源码包内 Makefile 无 check/test 目标，仓库无 tests/ 目录） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | 上游未提供任何可执行测试套件 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无 |
| 集成测试 | 0 | 不变 | 上游无 |
| 鸿蒙特有测试 | 11 | 新增（+11） | test_package/test_nift.sh：真实执行打包 nift/nsm 二进制的 11 项消费者功能断言（双入口 --version、init-html/init 建站、静态资源镜像、自定义模板 + $[title]/@content、多页面、hash 增量构建、内嵌 Lua 引擎 nift run） |
| **合计** | **11** | **+11（适配后从 0 → 11）** | 上游 0 → 适配后 11 |

> **测试用例增量小结**：上游 0 项 → 适配后新增 11 项，净增 **+11**。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（patches/ 为空，未改动任何上游源文件与测试）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（见下）

> - **补全的测试范围**：为 nift 核心功能新增 11 项消费者功能断言（覆盖双入口版本一致性、静态网站初始化与构建、模板引擎变量替换、多页面与增量重建、内嵌 Lua 脚本执行）
> - **补全原因**：上游仅提供静态站点生成引擎源码，无正式测试框架（Makefile 无 check/test 目标、仓库无 tests/ 目录），无法按常规运行上游测试
> - **新增测试文件清单**：
>   1. `archives/n/nift/3.0.3/test_package/test_nift.sh` — 11 项消费者功能断言脚本（真实调用打包产物）
>   2. `archives/n/nift/3.0.3/test_package/conanfile.py` — test() 经 CONFIG_SHELL 指定的 bash 执行测试脚本
>   3. `archives/n/nift/3.0.3/test_package/MANIFEST.yml` — 测试元数据（如实声明上游 no_tests）

## 验证结果

- 编译状态：通过（本地 conan create RC=0 + conan-verify 8 道门禁全 PASS；远程 CI #39054 ✅ 通过）
- 上游测试用例通过率：0/0（N/A，上游无测试套件可运行）
- 新增测试用例通过率：11/11（**100%**）
  - `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":11,"passedCount":11}`
  - `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`（上游无 check/test 目标，如实声明）

## 测试通过率汇总

| 指标 | 数值 | 说明 |
|------|------|------|
| **上游测试用例通过率** | 0/0（N/A） | 上游 v3.0.3 无任何测试套件（无 check/test 目标、无 tests/ 目录），无可运行用例 |
| **适配后测试用例增加** | **+11**（0 → 11） | test_package 补全 11 项消费者功能断言（真实执行打包 nift/nsm 二进制） |
| **适配后测试用例通过率** | **11/11（100%）** | 本地 W3 与远程 CI #39054 均全部通过 |

## 补充说明

- **依赖**：自包含（内嵌 Lua-5.3、exprtk、rapidjson、hashtk），无外部 conan 依赖
- **构建系统**：纯 Makefile；`LUA_VERSION=5.3` 走内嵌 Lua-5.3 的 generic 目标以绕开 LuaJIT 分支；CC/CXX 经最外层 make 命令行（MAKEFLAGS）传播以覆盖 Lua 子构建硬编码的 `CC=gcc`
- **打包**：上游 `make install` 依赖 chmod（HMDFS E046 拒绝），配方 package() 以 copy2 等价替代
- **产物验证**：nift / nsm 均为 aarch64-unknown-linux-ohos 可执行 ELF；无系统同名库冲突（R26 通过）
- **质量门禁**：W3 本地 CI（build_and_test.sh L0/L1/L1e/L2/L4/L5）通过；W4 独立审计 verdict=pass（P0/P1=0）
- **已知限制**：上游无官方单测可比对，功能验证以 11 项真实调用二进制的消费者断言代替（已如实声明 no_tests）
