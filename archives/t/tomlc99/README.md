# tomlc99 0.0-git20260130 — OpenHarmony 编译记录

## 基本信息
- 软件: tomlc99（TOML v1.0.0 compliant parser written in C99）
- 版本: 0.0-git20260130（上游 master-only 无 release tag，按仓库 git 快照惯例 0.0-gitYYYYMMDD；锚定 tarball 内容日期 2026-01-30）
- 构建系统: 手写 Makefile
- 目标: ohos-aarch64（HarmonyOS PC）
- 编译日期: 2026-10-03
- 上游: https://github.com/cktan/tomlc99 （单文件库 toml.c + toml.h；零依赖纯 C99）

## 编译指导
```bash
# CC 从 Conan conf tools.build:compiler_executables:c 获取（R33），
# 不覆盖 CFLAGS——保留上游 -std=c99 -Wall -Wextra -fpic -O2 -DNDEBUG
make CC=<clang> -j1 all
# 产物: libtoml.a / libtoml.so.1.0 / toml_cat / toml_json / toml_sample
```

## 补丁清单
| 补丁文件 | 说明 |
|---------|------|
| 0001-makefile-soname.patch | 共享库链接规则加 `-Wl,-soname,libtoml.so.$(LIB_VERSION)`，使 libtoml.so.1.0 携带相对 DT_SONAME（上游任何平台都缺失；CI L5a 门禁要求） |

## 已知限制
- 上游 README 声明库 OBSOLETE（继任 tomlc17）；C99 兼容面稳定，stdex 62 样例全绿
- test1（Go toml-test）/test2（toml-spec-tests+jq）套件需 Go 工具链/网络克隆/jq，CI Worker 环境不满足，豁免（定性见版本级 notes.md）

## 功能验证
```bash
# TOML 转储（stdin 或文件）
echo 'a = 1' | toml_cat
# TOML -> JSON
echo 'a = [1, 2]' | toml_json
```

## 产物
- libtoml.so.1.0（DT_SONAME=libtoml.so.1.0）+ libtoml.so（开发符号链接）
- libtoml.a（shared=False 变体）
- toml_cat, toml_json（静态链接 libtoml.a，随包即用）
