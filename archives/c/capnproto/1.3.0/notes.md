# capnproto 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- 状态: built（本地 conan create 验证通过，制品仓 upload 由 PR 合并后 CI release 流水线执行）

## 编译步骤

```bash
# 源码：官方 capnproto.org 发布归档（SHA-256 098f824a…，与 conandata.yml 一致）
curl -fsSL -o capnproto-v1.3.0.tar.gz https://capnproto.org/capnproto-c++-1.3.0.tar.gz
sha256sum capnproto-v1.3.0.tar.gz   # 098f824a495a1a837d56ae17e07b3f721ac86f8dbaf58896a389923458522108

# Conan 配方构建（OHOS aarch64 profile，host=build=OHOS）
conan create archives/c/capnproto/1.3.0 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 结果：库本体 100% 编译成功，test_package 4/4 PASSED

# 上游测试（BUILD_TESTING=ON 独立构建，TMPDIR 规避 /tmp 只读）
cmake -S <src> -B <build> -DBUILD_TESTING=ON \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DCMAKE_CXX_FLAGS=-stdlib=libc++ \
  -DWITH_OPENSSL=OFF -DWITH_ZLIB=OFF -DWITH_FIBERS=OFF -DEXTERNAL_CAPNP=OFF \
  -DCMAKE_CXX_EXTENSIONS=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build <build> --target kj-tests capnp-tests kj-heavy-tests capnp-heavy-tests capnp-evolution-tests -j8
TMPDIR=~/tmp ./kj-tests && ./capnp-tests && ./kj-heavy-tests && ./capnp-heavy-tests && ./capnp-evolution-tests

# 鸿蒙专项测试（对已发布包产物做消费者视角验证）
/data/service/hnp/bin/clang++ -std=gnu++17 -stdlib=libc++ -fPIC -I<pkg>/include \
  reports/ohos-specific-test.cpp <pkg>/lib/libcapnp.a <pkg>/lib/libkj-async.a <pkg>/lib/libkj.a \
  -lpthread -o ohos-specific-test && TMPDIR=~/tmp ./ohos-specific-test
# 结果：5/5 PASSED
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Conan toolchain 生成 `CMAKE_CXX_EXTENSIONS OFF`，capnproto 编译报需要 GNU 扩展 | Conan CMakeToolchain 对 cppstd=17 强制标准 -std，覆盖 cache_variables | generate() 设 `tc.cache_variables["CMAKE_CXX_EXTENSIONS"]=True` 后，对生成的 conan_toolchain.cmake 做字符串补丁 OFF→ON（知识草稿 E543） |
| 2 | `CMake Error: Compatibility with CMake < 3.5 has been removed` | CMake 4.x 移除 <3.5 兼容策略 | `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（复用既有草稿 DRAFT-E321） |
| 3 | 上游测试 16 项失败（mkstemp/mkdtemp/AF_UNIX bind 到 /tmp、/var/tmp） | OHOS /tmp、/var/tmp 只读挂载；测试硬编码路径，TMPDIR 无法规避 | 不改上游源码；用例如实计入失败并给出恢复条件（挂载可写 tmpfs）；TMPDIR 规避其余可规避用例（知识草稿 E544） |
| 4 | test_package 消费者测试 `capnp::Text::Builder` 无 set 成员 | capnp API 形态：Text::Builder 无 set | 改用 `capnp::List<uint32_t>` 根做 messageToFlatArray + FlatArrayMessageReader 往返 |
| 5 | 鸿蒙专项测试 kj filesystem 绝对路径抛异常；two-way pipe 端为 Own 指针 | kj 1.3.0 API：filesystem 仅相对路径（getCurrent）；Own<> 需 -> 访问 | 用 `fs->getCurrent()` 相对路径；`pipe.ends[0]->` 指针访问 |
| 6 | 官方源 GitHub 下载超时/404 | 网络限制；GitHub tag 与官网归档差异 | 用官方站点 https://capnproto.org/capnproto-c++-1.3.0.tar.gz（官方正式源，R39 合规） |

## 源码修改

上游库源码零改动，适配全部收敛在配方配置与受控补丁：

- `patches/0001-serialize-test-use-test-tmpdir.patch`（1 个，已注册于 conandata.yml patches list）：
  将 `src/capnp/serialize-test.c++` 的 Serialize/FileDescriptors 用例 mkstemp 路径由硬编码 `/tmp/...` 改为读取 `TEST_TMPDIR` 可写目录（与 kj filesystem-disk-test 同策略），修复 OHOS /tmp 只读平台下的用例失败（r02 验证、r03 固化）
- `run-upstream-tests.sh`（测试运行配置）：以 `TEST_TMPDIR=<可写目录>` 运行上游测试，恢复 12 项 filesystem-disk 用例（上游原生支持 `getenv("TEST_TMPDIR")`，无需改源码）

## 依赖版本

- 零强制依赖（可选 OpenSSL/Zlib/Fibers 全部关闭，WITH_* = OFF）
- 工具链：OHOS SDK clang 15.0.4（aarch64-linux-ohos），CMake 4.1.2

## 验证结果

```bash
# W3 本地 CI 模拟（finish step5）：通过（.ci-result.json exit_code=0）
# 上游测试双口径台账（reports/test-report.md，r03 终态）：
#   源码声明总数 1069；当前配置可执行 1009；通过 1006；失败 3（文件系统能力限制）
#   全量通过率 1006/1069 = 94.1%；可执行集合通过率 1006/1009 = 99.7%
#   r01 基线：993/1069 = 92.9%（失败 16）；r02/r03 经 TEST_TMPDIR + 受控补丁恢复 13 项
#   剩余 3 项失败：AsyncIo/UnixSocket（AF_UNIX 路径 bind errno 1）、DiskFile（fallocate punch hole errno 13）、
#   DiskDirectory link（hardlink EPERM）——均为 OHOS 文件系统能力限制，恢复条件见 test-report.md r03 段
# test_package：4/4 PASSED（conan create，补丁注册后回归）
# 鸿蒙专项测试：5/5 PASSED（ohos-specific-test）
# conan-verify：G1/G0/G2/G3/G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（静态、可选依赖关、组件齐全） |
| conandata.yml | 官方 HTTPS 源 + SHA-256 + patches list 注册 |
| test_package/ | 消费者测试（4 断言真实逻辑） |
| patches/0001-serialize-test-use-test-tmpdir.patch | 受控补丁：serialize-test mkstemp 路径改读 TEST_TMPDIR（OHOS /tmp 只读平台） |
| run-upstream-tests.sh | 上游测试运行配置（TEST_TMPDIR 可写目录策略，恢复 12 项 filesystem-disk） |
| commands.json | CLI 工具声明（capnp/capnpc-c++/capnpc-capnp，1.3.0） |
| reports/upstream-test-ledger.md | 上游测试全量枚举台账（72 文件/1069 用例） |
| reports/test-report.md | 双口径测试统计报告 |
| reports/ohos-specific-test.cpp | 鸿蒙专项测试源码 |
| reports/baseline-isolation-audit.md | W2/W3 基线隔离复验审计 |
| reports/knowledge-candidate-ledger.md | 知识候选台账（四范围查重+七轴+路径判定） |
| knowledge/drafts/E543-draft-*.kv/.md | 新知识草稿：CXX_EXTENSIONS toolchain 补丁 |
| knowledge/drafts/E544-draft-*.kv/.md | 新知识草稿：/tmp、/var/tmp 只读测试路径台账 |

## 注意事项

- W2/W3 曾命中其他库基线文件 `archives/u/util-linux-login/2.42.2/.ci-trigger`（提交前已存在、git 跟踪、HEAD 内）：已按隔离复验协议处理（记录路径+隔离前 SHA-256 → 临时隔离 → 复跑 → 原样恢复 → 恢复后哈希一致），未修改、未提交该基线文件；详见 reports/baseline-isolation-audit.md
- 制品仓 upload 仅由 PR 合并后的 CI release 流水线执行，本任务本地状态为 built
- /tmp、/var/tmp 只读为 OHOS 平台限制；相关 16 项上游测试失败与库缺陷无关，恢复条件为挂载可写 tmpfs
---

**编译结束**: 2026-09-07 18:52
**最终状态**: built
