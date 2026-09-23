# E617 — autotools 代码生成器无已发布 conan 包：gperf 走 missing 包装器 + perl 走 tool_requires

> Contributor: libfreehand-tools 0.1.2 适配 | Status: Draft | Updated: 2026-09-20
> 对应：`knowledge/drafts/E617-draft-3C7A.kv`
> 触发场景：`src/lib/Makefile.am` 的 `BUILT_SOURCES = tokens.h tokenhash.h` 需要
> `gentoken.pl`(perl) + `gperf` 两个代码生成器

## 错误签名
```
missing: gperf
gperf: command not found
No rule to make target 'tokenhash.h'
use of undeclared identifier ...in_word_set
```

## 现象与迷惑点

configure 日志里出现：

```
GPERF='${SHELL} /…/b/missing gperf'
```

**这不等于构建一定失败**：automake 的 `missing` 包装器会在**构建期重新从 PATH 解析** `gperf`，
找到就真实执行、找不到才退出 127。libfreehand-tools 0.1.2 实测就是这个形态——configure 期
`AC_PATH_PROG` 没命中，但构建期 `missing gperf` 成功调起了 `/data/service/hnp/bin/gperf`，
产物 `tokenhash.h` 13 258 B、头部 `/* C++ code produced by gperf version 3.1 */`。

第二个迷惑点：生成命令通常写成

```make
tokenhash.h : tokens.gperf
	$(GPERF) --compare-strncmp -C -m 20 tokens.gperf | $(SED) … > tokenhash.h
```

**管道吞掉 `missing` 的退出码**。若生成器真的缺失，make 不会失败，只会留下**空文件**——
好在消费该头文件的 TU 紧接着就会编译失败（未声明标识符），属**响亮失败**而非假绿。
判据：不要只看 configure 的 `GPERF=` 取值，要查「生成物是否非空 + 头部是否带生成器版本」。

## 根因

| 生成器 | 制品仓状态 | 可用手段 |
|---|---|---|
| `perl` | `perl/5.42.2.3` 已发布（`conan install --build=never` rc=0） | `tool_requires("perl/5.42.2.3")`，conan 自动放上构建 PATH |
| `gperf` | `archives/g/gperf/3.1` **只有配方、无 binary**（`conan install --requires=gperf/3.1 --build=never` → `Unable to find 'gperf/3.1' in remotes`） | 不能 tool_requires（R36：依赖必须先发布）；依赖 HNP 提供的 `/data/service/hnp/bin/gperf`（设备与 CI worker PATH 同源，先例 `archives/l/libhubbub/0.3.8`） |

## 识别特征
- **Severity**: 🟡 Medium
- **Trigger tool**: make / configure
- **Phase**: build
- **Pattern**: `AM_MISSING_PROG.*(GPERF|PERL)|BUILT_SOURCES\s*=.*(tokenhash|gperf)`
- **Category**: autotools, codegen, toolchain, ohos, conan

## 修复方案

```python
# conanfile.py
def build_requirements(self):
    self.tool_requires("pkgconf/3.0.5")
    # 制品仓已发布的 perl：gentoken.pl 生成 tokens.gperf（BUILT_SOURCES）
    self.tool_requires("perl/5.42.2.3")
    # 注意：gperf 无已发布 binary，不能 tool_requires；走 HNP PATH
```

自证生成器真跑过（写进 notes.md 证据段）：

```bash
grep -n "missing gperf" <build-log>
head -1 <build>/src/lib/tokenhash.h     # /* C++ code produced by gperf version 3.1 */
```

## 参考实现
- `archives/l/libfreehand-tools/0.1.2/conanfile.py`（perl tool_requires + la-free shadow）
- `archives/l/libhubbub/0.3.8`（Makefile 增加 gperf 生成规则、未 tool_requires 的先例）
- `archives/g/gperf/3.1/notes.md`（配方存在但未发布 binary）

## 验证方法
1. `conan install --requires=gperf/3.1 --build=never` → rc=1（不可 tool_requires 的正面证据）
2. `conan install --requires=perl/5.42.2.3 --build=never` → rc=0
3. 构建日志出现 `/…/p/perl…/p/bin/perl …/gentoken.pl …`（tool_requires 生效）
4. 构建日志出现 `missing gperf --compare-strncmp -C -m 20 tokens.gperf`，且 `tokenhash.h`
   非空、头部为 gperf 3.1 生成标记
