# list 0.4.1 适配笔记

### 对话 #1 (2026-09-18, pc2-13)
### 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 configure 脚本）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 / llvm-ar / llvm-ranlib
- 状态: published

## 编译步骤

```bash
# 获取官方 tag 源码
python3 scripts/ohc-run.py init-build list 0.4.1 --url=https://github.com/clibs/list/archive/refs/tags/0.4.1.tar.gz
sha256sum list-0.4.1.tar.gz   # 1ed72cc11d086e3e40cd6112867cc4102cddf5f008213da5de6e2db587b74340

# 手动编译验证
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib    # 产出 build/libclibs_list.a + .so.0.4.1
make test CC=clang AR=llvm-ar RANLIB=llvm-ranlib && ./bin/test   # 12/12 通过

# 配方生成与验证
python3 scripts/ohc-run.py conan-init list 0.4.1
python3 scripts/ohc-run.py conan-verify list 0.4.1    # G1-G4 全 PASS

# finish（W2 原子性 + W3 本地编译验证）
python3 scripts/ohc-run.py finish list 0.4.1 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G2 首次失败 "No targets specified and no makefile found" | basic_layout 使 build folder 位于 build-release/，make 未在 source_folder 内执行 | build() 中 `self.run(..., cwd=self.source_folder)` |
| 2 | test_package 报 "Library 'clibs_list' not found" | package() 中 copy 保留 build/、src/ 中间层级，CMakeDeps 找不到库 | copy() src 参数精确到 source_folder/build 与 source_folder/src |
| 3 | E017 镜像注入在归档目录残留 conandata.yml.ghfast-bak/.orig | conan-verify 临时注入 ghfast.top 镜像 | finish 提交前清理残留（JC1 拦截点） |
| 4 | 鸿蒙专项测试 dlopen SONAME 失败（EACCES） | 本设备用户区自建 .so 经 dlopen/DT_NEEDED mmap(PROT_EXEC) 被平台 MAC 拒绝 | 按平台静态链接惯例（R26），鸿蒙专项测试改用静态链接 + readelf 静态核验 SONAME/符号 |

## 依赖版本

- 无第三方依赖（纯 C99 + 系统 libc）；编译链 clang 15.0.4 / GNU Make 4.4.1 / cmake 4.1.2（test_package 用）

## 验证结果

```bash
# 上游测试 12/12 通过（见 reports/upstream-test.log）
./bin/test   # ... 100%

# 鸿蒙专项 3/3 通过（见 reports/ohos-test.log）
./bin/ohos_test   # HarmonyOS 专项测试 3/3 通过

# 消费者用例通过（见 reports/consumer-test.log）
./bin/test_consumer   # consumer test (public API via clibs/list.h): OK

# W3 本地 CI（见 reports/w3-local-ci.log）
# Total 1 / Success 1 / Failed 0 / Pass rate 100%
```

## 交付物

| 文件 | 说明 |
|------|------|
| packaging/list-0.4.1-ohos-aarch64.tar.gz | release 静态库 + 头文件 |
| packaging/list-0.4.1-debug.tar.gz | debug 静态库 + 头文件 |
| test_package/ | 消费者用例 + 鸿蒙专项用例（conan create 自动验证） |
| reports/ | conan-verify-report / test-report / w3-local-ci / 上游测试日志等 |

## 注意事项

- list 为纯头文件+源码的简单双向链表 C 库，无 configure、无依赖、无 CLI 产物（不生成 commands.json）。
- 上游 12 个测试函数全部在 test.c，main() 逐一调用；10,000,000 节点的 benchmark.c 依赖开发依赖 `bench`（不在 tag 内），不计入用例。
---

**编译结束**: 2026-09-18 17:15
**最终状态**: published
