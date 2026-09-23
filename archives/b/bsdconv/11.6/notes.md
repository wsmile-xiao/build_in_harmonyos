# bsdconv 11.6 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

```
make clean
make CC=clang -j1          # 纯 Make 构建（无 configure），生成 libbsdconv.so.11 + 4 个 CLI + codec 模块
make install PREFIX=<prefix>  # 安装 bin/lib/include/share/bsdconv 共 413 个文件
```

依赖发布检查（W0）：bsdconv 为纯 C 实现，无外部依赖，无需依赖适配。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 3 阶段转换（如 `ASCII:COUNT:ASCII`）报 EINVAL | 上游 `bsdconv_unpack` 的 VLA `phase_off[i+1]` 存在 off-by-one：`while((phase_off[i]=strsep(...))!=NULL)` 在 strsep 返回 NULL 时仍写 `phase_off[phasen+1]=NULL`，越界写栈导致 clang15/OHOS 下未定义行为 | 补丁 0002：VLA 扩为 `phase_off[i+2]` |
| 2 | libbsdconv.so 缺 DT_SONAME（CI L5a 门禁失败） | 上游 Makefile 链接共享库未加 `-Wl,-soname` | 补丁 0001：libbsdconv 目标加 `-Wl,-soname,${SHLIBNAME}` |
| 3 | OHOS `uname -s` 返回 HarmonyOS，Makefile `-ldl` 分支不触发 | `ifeq (${UNAME_S}, Linux)` 条件不匹配 | 无需修复：OHOS libc 原生提供 dlopen/dlsym/dlclose，链接与运行均正常 |

## 源码修改

- `patches/0001-Makefile.patch`：libbsdconv 链接加 `-Wl,-soname`（portability）
- `patches/0002-src-libbsdconv.c.patch`：修复 `bsdconv_unpack` VLA off-by-one（portability）

## 依赖版本

- 无编译依赖（纯 C）
- 上游测试：testsuite/api.c（C API）、testsuite/conversion.py（Python2 语法 + 依赖未分发的 python-bsdconv 绑定，无法在 OHOS Python3 运行）

## 验证结果

```
# 上游官方 C API 测试
./testsuite/api   →  API tests passed（5 组断言）

# test_package 自研断言（conan create 消费测试）
create 3-phase ASCII:COUNT:ASCII  → PASS（VLA 修复回归）
bsdconv_pack                      → PASS
insert_phase / replace_phase      → PASS
replace_codec / insert_codec      → PASS
端到端 utf-8:width:（to 阶段 null） → PASS（FULL/HALF 计数）
端到端 utf-8:zhcn:big5            → PASS（"中文"→a4a4 a4e5）

# W3 本地 CI（build_and_test.sh）
conan create → 100% pass（JC/L0/L1/L5 全过，SONAME 门禁通过）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 项目配方（编译器走 conf，R33 合规） |
| conandata.yml | 官方 GitHub URL + sha256 + 2 补丁声明 |
| test_package/ | test.c（9 断言）+ conanfile.py（直接编译）+ MANIFEST.yml |
| commands.json | CLI 工具声明（bsdconv 等 4 个可执行文件，R38） |
| patches/ | 0001-Makefile.patch、0002-src-libbsdconv.c.patch |

## 注意事项

- bsdconv CLI 不支持 `--version/--help` 参数（`--version` 会被当作 conversion 语法解析报错），L2 冒烟测试对该 4 个 CLI 的 version/help 检查为 skip，属上游 CLI 设计，不影响功能；可执行性由 test_package 端到端转换测试验证
- 运行时需通过 `BSDCONV_PATH` 环境变量（或编译宏）定位 `share/bsdconv` 模块目录
- conan-verify 的 G2 在本机因 SKILL 工具 E017 自动注入 ghfast.top 镜像（本机不可达）而失败，但手动 conan create 使用官方 GitHub URL 已完整通过（主包 + test_package 9 断言全过），W3 本地 CI 亦通过；远端 CI 使用官方源不受影响

---

**编译结束**: 2026-09-06
**最终状态**: built
