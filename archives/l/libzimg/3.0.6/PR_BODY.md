## PR 信息
- **三方库名称**：libzimg（不含版本号）
- **上游版本**：3.0.6
- **上游仓库地址**：https://github.com/sekrit-twc/zimg
- **适配路径**：路径 B（贡献创新：贡献 libtool -nostdlib 丢失 clang_rt.builtins 的 aarch64 fp128 链接知识，草稿见 knowledge/drafts/DRAFT-13534-libzimg-3.0.6-libtool-nostdlib-builtins.kv+.md）
- **使用知识库**：E114（umask 077 → 022，configure 生成后修正）、E206（HMDFS 临时目录权限，同族规避）

> 源码包 URL（conandata.yml）: https://github.com/sekrit-twc/zimg/archive/refs/tags/release-3.0.6.tar.gz （SHA-256 见 conandata.yml；上游 tag 为 `release-3.0.6`，带 `release-` 前缀）

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 122 | gtest 1.14 单元套件：96 通用用例（api 3 / colorspace 20 / depth 13 / graph 44 / resize 16）+ 26 个 aarch64 NEON 用例（--host=aarch64-linux 时由 configure 注册：colorspace 2 / depth 18 / resize 6），实测命令 `./test/unit_test --gtest_list_tests` |
| 集成测试 | 0 | 上游无独立集成测试目录 |
| 其他测试 | 0 | — |
| **合计** | **122** | 上游 `make check`（TESTS = test/unit_test）注册的全部用例 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 122 | 不变 | `make check -j1` 在 build() 内真跑，122/122 全部通过（gtest 输出：`[  PASSED  ] 122 tests.`，含 musl-libm 精确浮点参照库链入） |
| 集成测试 | 0 | 不变 | — |
| **鸿蒙特有测试** | 2 | 新增 | ① test_package 端到端深度转换（BYTE full→WORD limited，走 aarch64 NEON depth 内核，输出范围钳位校验）；② test_package resize 图构建+执行（16x16→8x8 float grey，NEON resize 内核），均真实链接已签名的 libzimg.so 运行 |
| **合计** | **124** | +2 | 122 上游全跑全过 + 2 个鸿蒙特有消费者测试通过 |

## 上游测试用例减少原因
无减少：适配后上游 122 个用例全部注册并全部通过（122/122，100%）。

## 上游测试用例修改说明
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在修改（逐条：文件路径+修改原因+修改内容）

## 补全测试用例说明
- [ ] **否**，上游已有测试覆盖
- [x] **是**，上游无测试用例，适配后补全（补全范围+原因+新增文件清单）

（说明：上游已有完整 gtest 套件；本 PR 额外补全的 test_package/test.cpp 为鸿蒙消费者验证，见"鸿蒙特有测试"行，非对上游测试的补全。）

## 验证结果
- 编译状态：通过（conan create 全绿）
- 上游测试用例通过率：122/122（100%）
- 新增测试用例通过率：2/2（100%）

### 编译验证
- 编译器: clang 15 (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: autotools（release tarball 无生成文件，配方内 bootstrap：conan tool_requires automake/1.18 + libtool/2.5.4.1 + hnp autoconf → aclocal/autoconf/libtoolize/automake → ./configure）
- 配置选项: `--build=aarch64-linux --host=aarch64-linux --enable-unit-test STL_LIBS=-lc++`（device-native 构建，host=aarch64 自动启用 ARM/NEON 后端；STL_LIBS 覆盖 zimg.pc 的 -lstdc++ 默认为 OHOS libc++）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | libzimg.so.2.0.0（shared，已 OHOS code-sign）+ zimg.h/zimg++.hpp + zimg.pc（Libs.private: -lc++）|
| 产物存在性 | ✅ | conan create 验证（Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created）|
| ELF 格式 | ✅ | aarch64-unknown-linux-ohos |
| 运行测试 | ✅ | 122/122 上游用例 + 2/2 消费者测试 |

## 补丁说明
无补丁（选项配置适配）。所有平台适配通过配置参数与配方逻辑完成：
- E114 家族：configure 生成后 `umask 077` → `umask 022`（HMDFS 临时目录权限，配方内 sed 修正）
- OHOS 链接修正：libtool 共享库链接带 `-nostdlib` 丢隐式 builtins，显式补 `-lclang_rt.builtins`（matrix.cpp 的 `RowMatrix<long double>` 在 aarch64 上为 fp128，引用 __addtf3 系符号）
- gtest 源码：上游 tarball 的 test/extra/googletest 是空 submodule，conandata 附官方 v1.14.0 tarball 解至该位置（保持 configure.ac 原生 cmake 子构建形态；v1.14.0 为最后支持 C++14 的版本，与 zimg CXXSTD=c++14 匹配，1.15+ 需 C++17）
- 运行环境：unit_test/consumer 运行补 SDK libc++_shared.so 路径（LD_LIBRARY_PATH，配方内显式构造）

## 依赖
- automake/1.18（tool_requires，已发布）
- libtool/2.5.4.1（tool_requires，已发布）
- 无运行时依赖（零依赖件；pthread/m 由系统提供）

## 补充说明
- 版本号策略：3.0.6 为上游正式版本号；仓内另有 `archives/z/zimg/3.0.6`（直编配方，制品仓包名 zimg/3.0.6），本 PR 为平台任务 #13534 的 libzimg 包（autotools 标准构建 + 上游测试闭环），制品仓无 libzimg/3.0.6，两包并存不冲突
- 已知限制：无（122 上游用例含 26 个 NEON 用例全过；fp128 链接问题已通过 builtins 显式链接解决）

## 知识库贡献（路径 B）
- **关联 issue**: #3055（libtool -nostdlib 丢失 clang_rt.builtins——aarch64 fp128 软浮点符号运行时未定义）
- **草稿**: knowledge/drafts/DRAFT-13534-libzimg-3.0.6-libtool-nostdlib-builtins.kv + .md（成对，五要素齐：error_signature/root_cause/solution/fallback/verify_builds=48908）
- **查重**: 知识图谱零有效命中（E190 为 Perl XS 场景不同修复路径）；该坑系统性影响所有 OHOS aarch64 上 libtool 构建且含 long double 的 C++ 共享库，形态隐蔽（测试全过、so 带病）

