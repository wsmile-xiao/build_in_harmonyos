# pd-lua 0.12.23 适配笔记

## 编译环境
- 构建系统: makefile（Makefile + Makefile.pdlibbuilder 0.7.0，无 configure）
- 编译日期: 2026-09-30
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built（conan-verify 通过，详见 reports/）

## 编译步骤

```bash
# 依赖（已发布 ohpcd）：
#   lua/5.4.8.1   -> liblua.a（PIC，静态）+ lua.h 等头文件
#   puredata/0.54.1 -> include/pd/m_pd.h + s_stuff.h

# 手动编译（探索阶段）
make -j1 \
  PDINCLUDEDIR=<puredata>/include/pd \
  luaflags="-I<lua>/include" \
  lualibs="-L<lua>/lib -llua -ldl -lm"

# 安装（staging 隔离）
make install DESTDIR=$TEST_PREFIX PDLIBDIR=/lib/pd/extra <同上 flags>
# 产物: <prefix>/lib/pd/extra/pdlua/{pdlua.pd_linux,pd.lua,pdlua/,...}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报 `R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol luaL_alloc; recompile with -fPIC` | 本机 conan 缓存持有 lua/5.4.8.1 的旧修订包，其 liblua.a 非 PIC；制品仓最新修订为 PIC | `conan remove "lua/5.4.8.1:*" -c` 后重新 `conan install`，拉到最新修订（PIC）即正常链接 |
| 2 | `pdlua.pd_linux` 加载报 `luaL_openselectedlibs: symbol not found` | 首次编译产生的 pdlua.pd_linux.o 为旧头文件下残留的过期对象 | `make clean` 后全量重编；新对象正确引用 `luaL_openlibs` |
| 3 | `make -j2` 报 `jobserver mkfifo: Operation not permitted` | HMDFS 禁止 fifo 创建 | 统一 `make -j1` |
| 4 | `#include "s_stuff.h"` not found | puredata 头文件在 `include/pd/` 子目录，不在 `include/` | PDINCLUDEDIR 指向 `<puredata>/include/pd` |
| 5 | `make check` 报 `No rule to make target 'check'` | 上游 Makefile.pdlibbuilder 无 check/test 目标 | 记录为"上游无 check"，以 headless Pd 实例化全部示例外部替代（见 reports/test-report.md） |
| 6 | lua 无 pkg-config 文件（lua.pc） | lua 配方仅设 pkg_config_name 属性，未生成 .pc | 直接以 make 命令行覆盖 `luaflags`/`lualibs`，绕过 pkg-config |

## 源码修改

无（无需补丁；patches/ 为空）。

## 依赖版本

- lua/5.4.8.1（静态 liblua.a，PIC）
- puredata/0.54.1（m_pd.h/s_stuff.h，pd.pc）

## 验证结果

```bash
# pdlua 被 headless Pd 加载
pd -batch -nogui -nrt -path <pdlua-dir> -lib pdlua -send "pd quit"
# -> pdlua 0.12.23 (GPL) 2008 ... / Using lua version 5.4

# 37 个示例外部实例化、14 个教程补丁、3 个 Lua 脚本、2 个顶层 help 全通过（共 56 项）
# 详见 reports/test-report.md
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/pd/extra/pdlua/pdlua.pd_linux | Pd 外部共享库（dlopen 加载） |
| lib/pd/extra/pdlua/pd.lua | pdlua 的 Lua 运行时 |
| lib/pd/extra/pdlua/pdlua/ | 示例 + 教程目录 |
| lib/pd/extra/pdlua/pdlua-meta.pd | 元数据 |
| lib/pd/extra/pdlua/pdlua-help.pd / pdluax-help.pd | help 补丁 |

## 注意事项

- 产物是 Pd 外部（库类型），由 `pd -lib pdlua` 加载，非可链接库，无 bin/ 可执行文件 → 不需要 commands.json（R38）
- 若 CI 复现 non-PIC 链接错误：先 `conan remove "lua/5.4.8.1:*" -c` 再构建
---

**编译结束**: 2026-09-30 14:55
**最终状态**: built
