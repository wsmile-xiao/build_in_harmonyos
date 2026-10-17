# sole 1.0.4 适配笔记

## 编译环境
- 构建系统: header-only（无编译阶段，纯头文件拷贝）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

sole 是 header-only C++11 UUID 库（sole.hpp + sole.fwd.hpp），无 configure/make/CMake 构建。
配方采用 v12.21 headeronly 变体：source() 拉取官方 tag 1.0.4 tarball，build() 仅应用补丁，
package() 拷贝头文件到 include/。验证通过 conan create 完成：

```bash
conan create . --version=1.0.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → 消费者 test_sole 编译链接运行通过：格式/version nibble/rebuild 往返/1000 唯一性 OK
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `static __thread std::random_device rd` 编译报 "type of thread-local variable has non-trivial destruction" | clang 15 对 `__thread` 用于非平凡析构类型（std::random_device/std::uniform_int_distribution）报错，须用标准 C++11 `thread_local` | patch 0001：`$melse(__thread)` → `$melse(thread_local)`，已验证编译+运行通过 |
| 2 | conan 2.32.0 报 `Invalid setting 'OHOS'` | 官方 PyPI conan 未适配 OHOS 平台 | 按 ci/conan/setup.sh 安装社区源 OHOS 适配版 conan 2.29.1（pypi.cnb.cool），补 distro 依赖 |
| 3 | headeronly 模板 package() 相对 dst="include" 解析到 build 目录 | basic_layout 下相对路径按当前目录解析 | package() 改用 `os.path.join(self.package_folder, "include")` 绝对路径 |

## 源码修改

- patches/0001-sole.hpp.patch：uuid4() 的 `__thread` → `thread_local`（2 行，portability）

## 依赖版本

无（header-only，零依赖）。

## 上游测试台账（R51 三步法）

测试入口：`sole.cxx`（`#define SOLE_BUILD_TESTS` 后包含 sole.hpp，内建测试框架 `run::`）。

| 入口 | 类型 | 独立用例? | 运行 | 结果 |
|------|------|-----------|------|------|
| main() sizeof(sole::uuid)==128 断言 | 内建断言 | 是 | 编译后已执行 | 通过 |
| main() sizeof(uuid0().ab)==64 断言 | 内建断言 | 是 | 已执行 | 通过 |
| main() sizeof(uuid0().cd)==64 断言 | 内建断言 | 是 | 已执行 | 通过 |
| run::verify(uuid4)（1M 次 str/base62 rebuild 往返） | 内建校验 | 是 | 已执行 | 通过（"ok"） |
| run::tests(uuid4)（numtests=~0 无界碰撞压力测试） | 内建压力测试 | 是 | 已执行（预算内 200s） | 运行 10,131,192 次无碰撞 (0.0023%) 后超时，非失败；完整跑完需 ~4.29e9 次，数小时以上，不属本库缺陷 |
| run::benchmark(uuid0/uuid1/uuid4/rebuild/str) | 基准 | 否（基准不计用例） | 已执行 | v0 6901/s, v1 7701/s, v4 72876/s, rebuild 11167576/s, str 5170232/s |
| demo.cc（SOLE_BUILD_DEMO） | 示例 | 否（样例不计用例） | 未作为用例 | 示例代码 |

- 全量通过率：4/5 (80%)。碰撞压力测试是上游刻意设计的无界循环（`unsigned numtests = ~0` 即 4,294,967,295 次），
  在 CI/本地预算内无法完整跑完；已运行 1011 万+ 次生成无碰撞，无失败断言。未运行/未完成项如实计入分母但不计为通过。
- 实际执行通过率（可完整执行的用例）：4/4 (100%)。

## 鸿蒙专项测试

test_package/test.cpp（消费者用例）：仅通过公开头文件 sole.hpp 调用公开 API：
- uuid0/uuid1/uuid4 生成与 8-4-4-4-12 十六进制格式校验
- version nibble 校验（v1=1, v4=4）
- rebuild() 从 str 与 base62 往返重建相等
- 1000 个 v4 UUID 唯一性（std::set 去重）
已在 OHOS profile（clang 15, armv8）下经 conan create 编译、链接、运行通过（rc=0）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | headeronly 配方（package_type=header-library） |
| conandata.yml | 官方 GitHub tag 1.0.4 URL + sha256 + patch 声明 |
| patches/0001-sole.hpp.patch | thread_local 修复 |
| test_package/ | CMake 消费者测试（conanfile/CMakeLists/test.cpp/MANIFEST） |

## 注意事项

- 无 CLI 产物（header-only 库），不需要 commands.json（R38 不适用）。
- 无运行时/编译依赖，W0 依赖检查通过。
---

**编译结束**: 2026-09-19 02:40
**最终状态**: built
