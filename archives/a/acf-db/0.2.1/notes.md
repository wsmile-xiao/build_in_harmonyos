# acf-db 0.2.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

纯 Lua ACF 模块，无 C 编译。单一递归 Makefile：
1. `make -C <src> -j1 all` — `all:` 为空操作，仅校验 Makefile 语法
2. `make -C <src> install DESTDIR=<pkg> -j1` — 顶层 Makefile 将 `db*`（controller/model/menu/roles）复制到 `usr/share/acf/app/db`，并递归执行 `lib/` 的 install（helpers + `.lsp` 视图模板复制到 `usr/share/acf/lib`），再为 app/db 下的视图建软链

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI L1e 破坏性负向测试误判"假测试" | 本地 conan 缓存存在多个 acf-db 二进制包目录，负向复跑解析到未破坏的目录 | W3 前 `conan remove "acf-db/*" -c` 清缓存；test_package 改用 `os.environ` 注入包路径，精确指向被测包 |
| 2 | test_package env 传参无效 | Conan 2 `run()` 的 `env=` 只接受 env 文件名列表，不接受 `KEY=VALUE` | 改用 `os.environ["ACF_DB_PKG_ROOT"]` 注入 |

## 源码修改

无（上游 Makefile 仅用 `cp -a`/`mkdir -p`/`ln -sf`，无 coreutils `install`，OHOS 无需补丁）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| acf-core | 0.24.1 | 运行时框架（mvc.lua 分发），已发布 ohpcd 制品仓 |
| lua | 5.4.8 | acf-core 的运行时依赖 |

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # G2 PASS
conan-verify: G0-G4 + L2/L4/L5 PASS
build_and_test.sh acf-db/0.2.1   # L0/L1 PASS，L1e 负向测试确认真实依赖
test_acf_db.sh: PASS=8 FAIL=0（文件存在性 + luac 语法校验）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/acf-db-0.2.1.tar.gz | 8.3K | 上游源码 tarball（与 conandata.yml 一致） |

## 注意事项

- 纯 Lua 数据模块：无 bin/、无 lib 库，L2 smoke test 按规则跳过
- 运行时需 acf-core 提供 mvc 分发；测试期不依赖真实数据库（L1 只验证包装完整性）
---

**编译结束**: 2026-08-09 09:16
**最终状态**: built
