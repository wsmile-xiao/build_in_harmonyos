# microtar 0.1.0 适配笔记

## 编译环境
- 构建系统: custom（无上游构建系统，clang 直接编译）
- 编译日期: 2026-08-28
- 编译器: clang/clang++
- 状态: published

## 编译步骤

microtar 是单文件 ANSI C 库（`src/microtar.c` + `src/microtar.h`），上游无
Makefile/configure 构建系统。适配采用直接编译方式：

```bash
clang -fPIC -O2 -I src -c src/microtar.c -o microtar.o
llvm-ar rcs libmicrotar.a microtar.o
llvm-ranlib libmicrotar.a
```

安装到 staging：`microtar.h` → include/，`libmicrotar.a` → lib/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试脚本对 `mtar_next()` 语义理解错误，误判库有 bug | `mtar_next()` 只 seek 到下一条记录，归档结束标记 `MTAR_ENULLRECORD` 由随后的 `mtar_read_header()` 返回 | 修正测试：`mtar_next()` 后必须再调用 `mtar_read_header()` 才能检测到 ENULLRECORD |
| 2 | GitHub 直连下载超时 | 网络环境无法直连 github.com | 通过 ghfast.top 镜像下载源码包，放入 `$TMPDIR/builds/` 供 init-build 复用；conan-verify 的 E017 机制自动注入镜像 |

## 源码修改

无补丁（`patches: {}`）。上游源码未作任何修改。

## 依赖版本

无外部依赖（纯 ANSI C，仅使用标准库 stdio/stdlib/string）。

## 验证结果

```bash
# 功能验证（消费者集成测试，写入→读回→校验）
./test_microtar
# PASS: write/read round-trip ok
# ALL TESTS PASSED

# Conan 配方验证（8 道门禁 G0-G4 + L2/L4/L5）
conan-verify microtar 0.1.0 → ✅ 全部通过
conan create → G2 PASS（干净构建 libmicrotar.a）
W3 本地 CI 模拟（setup.sh + build_and_test.sh）→ ✅ 通过
```

测试覆盖 `mtar_open`（写/读）、`mtar_write_file_header`、`mtar_write_data`、
`mtar_finalize`、`mtar_close`、`mtar_read_header`、`mtar_read_data`、
`mtar_next`、`MTAR_ENULLRECORD` 结束标记，共 12 个断言边界，全部通过。

## 交付物

| 文件 | 说明 |
|------|------|
| libmicrotar.a | 静态库（clang + llvm-ar，-fPIC -O2） |
| microtar.h | 公共头文件 |
| test_package/test.c | 消费者集成测试（适配补充，上游无测试套件） |

## 注意事项

- 上游 v0.1.0 是唯一 release tag（2017 年），仓库无测试目录/测试目标。
- `mtar_next()` 不返回 ENULLRECORD，检测归档结束需在其后调用 `mtar_read_header()`。
- conan-verify 的 E017 镜像注入会临时改写 conandata.yml 的 url 为本地缓存路径，
  验证后需恢复为官方 GitHub 源（R39）。
