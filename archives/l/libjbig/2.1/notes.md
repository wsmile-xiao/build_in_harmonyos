# libjbig 2.1 适配笔记

## 编译环境
- 构建系统: makefile（jbigkit 纯 Makefile 项目，非 autotools）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）+ llvm-ar / llvm-ranlib
- 状态: built

## 编译步骤

jbigkit 为纯 Makefile 项目，无 configure 脚本。顶层 Makefile 通过 `export CC CFLAGS`
向子目录传递变量，因此以 make 命令行参数（最高优先级）传入交叉编译器：

```bash
make lib CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar \
     RANLIB=/data/service/hnp/bin/llvm-ranlib
make pbm CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar \
     RANLIB=/data/service/hnp/bin/llvm-ranlib
```

产物：`libjbig/libjbig.a`（JBIG1）、`libjbig/libjbig85.a`（T.85）、公共头文件
`jbig.h`、`jbig85.h`、`jbig_ar.h`，以及 pbmtools 命令行工具。

Conan 配方（archives/l/libjbig/2.1/conanfile.py）：
- `source()`：官方源下载 + strip_root，无补丁
- `build()`：`make lib` 传入交叉编译器（同历史已验证的 jbig 2.1 配方）
- `package()`：复制静态库与公共头文件，校验存在性
- `package_info()`：`cpp_info.libs = ["jbig"]`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 FAIL（conanfile.py 缺 export_sources） | 手工改写配方时遗漏模板自带方法 | 补回 `export_sources()` + `export_conandata_patches` 后 G1 通过 |
| 2 | W3 本地 CI JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | 无关历史基线（其他库的已提交空文件，不在本库允许范围） | 按 oh-executor 规则做索引级受限隔离→复验（W3 100% 通过）→无条件精确恢复（blob e69de29 一致） |

## 源码修改

无（无需补丁）。

## 依赖版本

无外部依赖（自包含纯 C 库）。

## 验证结果

上游测试（make test，全部 PASSED）：
- libjbig：T.82/T.85 编码/解码回环全部通过
- pbmtools：pbmtojbg/jbgtopbm/pbmtojbg85/jbgtopbm85 多分辨率编码/解码比对一致

Conan 验证（conan-verify，G1-G4/L2/L4/L5 全通过）：
- `conan create`（ohos-aarch64 profile）+ test_package 消费者测试通过：
  `OK: libjbig 2.1 encode/decode round-trip (16x16, 41 bytes)`

W3 本地 CI 模拟（build_and_test.sh）：1/1 包通过，L0-L5 全绿。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 构建，静态库） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | 真实消费者测试（JBIG1 编码/解码回环）+ MANIFEST.yml |
| packaging/libjbig-2.1-ohos-aarch64.tar.gz | release 打包 |
| packaging/libjbig-2.1-debug.tar.gz | debug 打包 |

## 注意事项

- jbigkit 顶层 Makefile `export CC CFLAGS` 会向子 make 传递环境，必须用命令行参数
  覆盖（优先级最高），不能依赖环境变量（R33）。
- 知识判定：path_a_no_knowledge（路径 A），无跨库新增知识候选。
