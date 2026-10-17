# protobuf 3.17.3 本地 CI + review 自检报告（local-ci-review）

> 主机：OHOS aarch64 真机；conan `ohos-aarch64`（clang15, libc++17, Release），with_zlib=ON（与发布一致）。
> 配方：开启 `protobuf_BUILD_TESTS=ON` + googletest v1.10.0 + zlib 链接适配（`ZLIB_LIBRARIES=zlib::zlib` + `0002-tests-link-zlib.patch` + test_package `find_package(zlib)`）。

## 1. 编译状态

- `python3 -m conans.conan create archives/p/protobuf/3.17.3 -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64`：**通过**（build + package created + test_package 4/4）。
- 产物（package `24249987a0782c07a1ee0a18e8fcd1eab4c765e9`）：`lib/libprotobuf.a` / `lib/libprotoc.a` / `lib/libprotobuf-lite.a` + `bin/protoc` + 104 头文件 + cmake/pkgconfig/licenses。

## 2. 测试通过率（如实）

| 测试集 | 数量 | 通过 | 通过率 | 说明 |
|--------|------|------|--------|------|
| 上游 gtest `tests`（full） | 2275 | 2275 | 2275/2275 (100%) | 200 test suites，真机执行 |
| 上游 gtest `lite-test` | 53 | 53 | 53/53 (100%) | libprotobuf-lite |
| 上游 gtest `lite-arena-test` | 2 | 2 | 2/2 (100%) | libprotobuf-lite Arena |
| **上游 gtest 合计** | **2330** | **2330** | **2330/2330 (100%)** | 真机执行，无失败/跳过 |
| test_package 消费者（any/serialize/json/arena） | 4 | 4 | 4/4 (100%) | 19 断言 |
| protoc 烟雾（`protoc --version`） | 1 | 1 | 1/1 (100%) | `libprotoc 3.17.3` |

> **conformance 测试**：protobuf 官方协议一致性测试（`conformance_test_runner`+`conformance_cpp`），在 **3.17.3 上游源码中无法构建运行**（上游缺陷：`conformance.cmake` 漏 `conformance_test_main.cc`，且其引用的 `text_format_conformance_suite.cc` 缺失），**非鸿蒙平台限制**。如实记为「无法执行（上游 3.17.3 源码缺陷）」，未虚报、未无理由剔除。

**上游测试适配率**：可执行上游测试基线 gtest = 2330，全部通过（**2330/2330 100%**）；conformance 因上游源码缺陷无法执行（已记录根因）。

## 3. 门禁复核（手动核验；conan-verify 因 conan CLI shebang 环境限制无法自动跑）

| 门禁 | 项目 | 结果 | 证据 |
|------|------|------|------|
| G0 | 预构建风险评估 | 非阻塞 | — |
| G1 | 配方完整性 | ✅ | conanfile + conandata + test_package 齐全 |
| G2 | conan create 干净构建 | ✅ | `Package created` |
| G3 | 系统同名库隔离 | ✅ | `readelf -d bin/protoc`：DT_NEEDED 仅 `libc++_shared.so`、`libc.so` |
| G4 | 产物完整性 | ✅ | bin/lib/include/cmake/pkgconfig/licenses 齐全 |
| L0 | 质量门禁 | ✅ | test_package 存在；conanfile `test()`+`self.run()`；MANIFEST.yml；无裸 self.run；无硬编码 remote；依赖 zlib/1.3.1 已发布；无重复版本；目录 `archives/p/protobuf/3.17.3/`；分支 `feat/protobuf-3.17.3`；settings 四字段；无 curl/wget |
| L2 | 烟雾测试 | ✅ | `protoc --version` → `libprotoc 3.17.3` |
| L4 | 安全扫描 | ✅ | Type=DYN（PIE）；GNU_RELRO；GNU_STACK RW（NX） |
| L5 | 产物基线 | ✅ | SHA256 见下 |
| JC | 垃圾文件 | ✅ | test_package 构建产物已清理 |
| KC | 知识库 | ✅ | 未新增 knowledge/drafts/ 条目 |

## 4. L5 产物基线（SHA256，with_zlib=ON 构建）

```
c4726fd3c632061a8a120b731b057c2e69ac8d0d65ccc596f3708393578ceef1  lib/libprotobuf.a
50ae1ba7a53426b0ebe1415d909632ca7642891b915639f8516806fa8d3292e4  lib/libprotoc.a
17a2d9b4909915c492ea5cf7992bb4f4e85ba2c29c491dbc910f4267a7d774c2  lib/libprotobuf-lite.a
11c325104071354f4d66695b11a989ab5bd9343c5e42e4f106fb25a4db69d84c  bin/protoc
```

## 5. review 自检

- `python3 scripts/ohc-run.py review protobuf 3.17.3`：**针对本库检查全 PASS**（打包产物/测试报告/提交自检/知识图谱合规），**无本库 P0/P1**。
- 唯一的 `FAIL` 为**全局知识库 E 编号冲突**（`E257`/`E321`…，属 knowledge/ 索引全局预存问题，本 PR 未改 knowledge/），与本库无关。

## 6. 不足项与说明

- conformance 测试因 **3.17.3 上游源码缺陷**无法构建运行（已记录根因），非鸿蒙/配方问题；可执行的上游测试（gtest）已 2330/2330 全过。
- `conan-verify` 自动执行受本机 conan CLI shebang 环境限制（系统解释器作为 shebang 被拒），已改为手动核验各关键门禁（G1-G4/L0/L2/L4/L5/KC/JC），均通过。

**最终通过率：上游 gtest 2330/2330 (100%) + 消费者 4/4 (100%) + protoc 1/1 (100%)**
