# Autotools 文档构建在无 texinfo 环境失败（Error 127）— 用 --disable-doc 规避

> 来源: libmicrohttpd 1.0.1 适配（task libmicrohttpd-1.0.1-r01），草稿 DRAFT-libmicrohttpd-1.0.1-texinfo-missing-disable-doc

## 问题

Autotools 项目执行 `make install`（含 `install-recursive`）时，`doc/` 子目录调用
`makeinfo`（或 `texi2any`）生成 `.info` 文档。构建/CI 干净环境未安装 texinfo
工具链时，`build-aux/missing` 包装脚本报：

```
build-aux/missing[81]: makeinfo: inaccessible or not found
WARNING: 'makeinfo' is missing on your system.
make[2]: *** [Makefile:543: libmicrohttpd.info] Error 127
```

Error 127 使整个 `make install` 在 doc 阶段中断（exit 2），随后 install-recursive
级联失败。库本身已编译成功，仅文档产物无法生成。

## 根因

autotools 的 `doc/Makefile.in` 无条件声明 info 目标（`MAKEINFO = $(SHELL) $(top_srcdir)/build-aux/missing makeinfo`），
`build-aux/missing` 在找不到 `makeinfo` 时返回 127。CI/容器环境默认不装 texinfo，
omit-docs 需要显式 configure 选项关闭。

## 方案

configure 阶段显式禁用文档构建：

```bash
./configure --prefix=... --disable-doc
```

libmicrohttpd 1.0.1 实测：`--disable-doc` 后 configure 摘要显示
`Build docs: no`，`make` 与 `make install` 均 exit 0，库产物（静态/动态库、头文件、
pkg-config）完整无缺。此选项只跳过 info/html 文档生成，不影响运行库功能。

Conan 配方固化方式（AutotoolsToolchain.generate()）：

```python
def generate(self):
    tc = AutotoolsToolchain(self)
    ...
    tc.configure_args.append("--disable-doc")
    tc.generate()
```

## 验证

- 修复前: `make install DESTDIR=...` → `makeinfo: inaccessible or not found` → Error 127 → exit 2（libmicrohttpd-1.0.1 install.log/install2.log）
- 修复后: configure exit 0（`Build docs: no`）+ make exit 0 + make install exit 0（configure4/5.log, install3.log）
- 产物核验: microhttpd.h、libmicrohttpd.a、libmicrohttpd.so.12.62.1、libmicrohttpd.pc 齐全

## 适用边界

- 适用: 任何 autotools C/C++ 库，在无 texinfo 的干净 CI/容器/交叉构建环境；需要静态/动态库产物但不需要 info/HTML 文档的场景
- 反例: 构建/CI 环境已安装 texinfo（`which makeinfo` 有输出）时无需 `--disable-doc`；明确需要发布文档时改 `tool_requires texinfo` 补工具

## 关联

- `similar_to`: E011（受影响软件列表提及 texinfo，但根因是 HMDFS umask，与本问题无关）
- 无 caused_by / prerequisite_of / conflicts_with

## 查重差异（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false |
| causal_duplicate | false |
| trigger_overlap | partial（E011 误关联提及 texinfo） |
| solution_overlap | false |
| combination_novelty | true（错误→根因→--disable-doc 组合未登记） |
| boundary_novelty | true（明确适用边界与反例） |
| test_migration_novelty | false |

## 证据文件

- `archives/l/libmicrohttpd/1.0.1/reports/knowledge-candidate-ledger.md`（候选 3）
- 构建日志（install.log / configure4.log / install3.log，见 task 回报 evidence）