# tomlc99 0.0-git20260130 适配笔记

## 基本信息
- 软件: tomlc99（TOML v1.0.0 compliant parser written in C99）
- 版本: 0.0-git20260130（上游 master-only 无 release tag，按仓库 git 快照惯例 0.0-gitYYYYMMDD，先例 asmjit 0.0-git20231115.1da9e4d；锚定 tarball 内容日期 2026-01-30）
- 上游: https://github.com/cktan/tomlc99 （单文件库：toml.c + toml.h；README 声明 OBSOLETE，继任者为 tomlc17，但 C99 兼容面稳定、stdex 全绿）
- 构建系统: 手写 Makefile（非 autotools/cmake）
- 目标: ohos-aarch64（HarmonyOS PC）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（aarch64 原生）

## W0 依赖检查
tomlc99 为纯 C99 零依赖库：toml.c 仅包含 libc 头文件（stdio/stdlib/string/ctype/assert/inttypes/errno），无任何 `requires()`，无系统库依赖（不需 -lm/-lpthread）。`conandata.yml` 无依赖段，制品仓预检通过。

## 编译步骤
```bash
# 上游 Makefile（未覆盖 CFLAGS，保留 -std=c99 -Wall -Wextra -fpic -O2 -DNDEBUG）
make CC=<conan conf 提供的 clang> -j1 all          # libtoml.a + libtoml.so.1.0 + 3 个工具
# Conan 打包: include/toml.h, lib/libtoml.so.1.0(+libtoml.so 链接), bin/toml_cat|toml_json,
#             test/stdex/(62 样例+期望输出)
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游产物 libtoml.so.1.0 无 DT_SONAME（readelf -d 无 SONAME 条目），CI L5a 门禁必挂 | 上游 Makefile 共享库规则 `$(CC) -shared -o $@ $^` 任何平台都不带 -Wl,-soname（手写 Makefile 常见遗漏，与 CMake 工程靠 Platform 模块注入 SONAME 的机制不同） | patches/0001-makefile-soname.patch：链接行加 `-Wl,-soname,libtoml.so.$(LIB_VERSION)`；产物 DT_SONAME=libtoml.so.1.0（相对路径，合规）。E383 是 CMake 侧镜像问题（CMAKE_SHARED_LIBRARY_SONAME_C_FLAG），本条为 Makefile 侧新场景，已录草稿 DRAFT-14412 |
| 2 | stdex/float6.toml 回归失败：toml_cat 输出 `sf6 = -nan`，期望 `nan` | musl/glibc 的 printf("%f") 对负 NaN 显示 `-nan`（符号位随 strtod("-nan") 保留）；TOML v1.0.0 规范明确 NaN 实际编码 implementation-specific（float6.toml 源码注释自证）。属 libc 显示层差异，非解析缺陷（parse 层 ok=1、位模式正确） | test_package 比对 harness 对**双方**做 `-nan`/`+nan`→`nan` 符号归一化（仅显示层，不改上游 .res 也不改 toml_cat/toml.c）；同时保留原始（未归一化）计数与逐例输出，61 字节精确 + 1 归一化 = 62/62 通过，nothing hidden。已录草稿 DRAFT-14413 |
| 3 | 上游 unittest/t1.c 用 `#include "../toml.h"` 相对路径引用父目录头文件，conan test_package 布局下无法直接编译 | 上游假设源码在 unittest/ 子目录、头文件在仓库根 | 零修改方案：test_package build() 把打包 toml.h 暂存 `<build>/`、t1.c 暂存 `<build>/upstream_unit/`——相对包含自然解析到打包头文件（CMakeLists add_executable 指向暂存路径）。t1.c 字节级原样归档（sha256 与 tarball 内一致：4c820e1a...） |
| 4 | Release 配置 -DNDEBUG 会把 t1.c 的 20 个 assert() 编译掉，测试变成空转 | 上游 Makefile Release CFLAGS 含 -DNDEBUG | CMakeLists 对 unittest_t1 目标加 `-UNDEBUG`（上游 toml_cat.c 自身同样用 `#ifdef NDEBUG #undef NDEBUG` 防护，同源意图） |

## 上游测试面真跑记录（本机 HarmonyOS PC aarch64 原生）
| 套件 | 上游入口 | 用例数 | 实跑结果 | 说明 |
|------|---------|--------|---------|------|
| unittest/t1.c | `make -C unittest && ./t1` | 1 程序 / 20 断言 | 20/20 PASS（exit 0） | UTF-8↔UCS 往返；test_package 内零修改重跑 |
| stdex | `bash RUN.sh` | 62 样例 | 62/62 PASS（61 字节精确 + float6 NaN 符号归一化，见问题 #2） | toml_cat 输出比对 .res；test_package 用打包产物重跑 |
| test1 | `bash build.sh && run.sh` | toml-test 全套 | 豁免 | 需 Go 工具链 + 网络 `go install github.com/toml-lang/toml-test/cmd/toml-test@latest`；CI Worker 无 Go 生态（能力矩阵：Rust/Go ❌）。上游 README 记录基线 129 passed/3 failed（3 个为 toml v1.0 允许数组混型前的旧断言） |
| test2 | `bash build.sh && run.sh` | toml-spec-tests | 豁免 | 需 `git clone https://github.com/cktan/toml-spec-tests.git`（网络）+ jq 工具（Worker 无）；其正面样例与 stdex 高度重叠 |

- stdex 62 样例中 19 个为负例（.res 内容为 `ERROR: line N: syntax error` 类文本）——toml_cat 对负例 exit 0、错误走 stderr，harness 按 RUN.sh 原样合并 stdout+stderr 比对。
- test1/test2 豁免定性：**CI Worker 环境外依赖**（Go 工具链/网络克隆/jq），非 OHOS 平台限制；两个套件的 TOML 解析语义已被 stdex 62 样例 + unittest 20 断言 + consumer 32 CHECK 覆盖（test1 官方套的部分能力）。

## 验证结果（本地 conan create，ohos-aarch64 profile）
- L0: pass（结构五件套齐：test_package/.c 源/MANIFEST.yml；patches 列表格式合规）
- L1: pass（ctest: consumer_test + unittest_t1；stdex runner 62/62；日志含 "Running test()" 与断言证据行）
- L1e: pass（破坏性反向验证：移走 lib/include/bin 后 conan test 失败=真依赖）
- L2: pass（bin/toml_cat、bin/toml_json 均支持 stdin 直读，`--version/--help` 按 TOML 解析报 syntax error 退出码 1 属预期——L2 为非阻塞 warn 不影响）
- L4: pass（唯一补丁仅加链接参数，无危险函数）
- L5: pass（readelf -d libtoml.so.1.0 含 SONAME=libtoml.so.1.0 相对路径；NEEDED 无绝对路径；无 .cmake 文件）

## 源码修改
- patches/0001-makefile-soname.patch: Makefile 共享库链接规则加 -Wl,-soname（1 行改动，portability）
- 其余零源码改动（toml.c/toml.h/toml_cat.c/toml_json.c/stdex/* 全部原样）

## 交付物
- include/toml.h
- lib/libtoml.so.1.0（DT_SONAME 合规）+ lib/libtoml.so（开发链接符号链接）
- lib/libtoml.a（shared=False 变体）
- bin/toml_cat、bin/toml_json（静态链接 libtoml.a，随包即用）
- test/stdex/（62 样例 + .res，test_package 回归资产）

## 注意事项
- toml_parse() 原地改写输入缓冲，消费者必须传可写 char[]
- toml_string_in/toml_string_at 返回的字符串与 toml_timestamp_in 的 ts 需调用方 free()
- 上游 README 声明库 OBSOLETE（继任 tomlc17），如后续有 tomlc17 需求应另立配方，不复用本包名
