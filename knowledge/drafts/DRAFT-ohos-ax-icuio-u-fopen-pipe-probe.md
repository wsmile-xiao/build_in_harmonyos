# DRAFT-ohos-ax-icuio-u-fopen-pipe-probe-kv1 — AX_ICUIO 管道探测 SIGPIPE（clang 下）

> 对应 KV：`knowledge/drafts/DRAFT-ohos-ax-icuio-u-fopen-pipe-probe.kv`
> 触发事件：cif-api 0.4.2 HarmonyOS PC 适配（configure AX_ICUIO 阶段失败）

## 问题（error_signature）

cif-api（COMCIFS CIF 2.0 C API）0.4.2 在 OHOS aarch64 本地适配时，configure 走到
`AX_ICUIO` 检查（确定 ICU I/O 的 `u_fopen()` 宏真实符号名）即中止：

```text
checking the real name of u_fopen()... error: write on a pipe with no reader
configure: error: Failed to determine the true name of u_fopen
```

## 根因（root_cause）

autoconf-archive 的 `AX_ICUIO` 宏（`m4/ax_icuio.m4`）为确定 `u_fopen()` 宏展开后的
真实符号名（ICU 77 → `u_fopen_77`），使用管道：

```sh
_ax_icuio_UFOPEN=`${CPP} ${CPPFLAGS} conftest.c |
    ${SED} -n -e '/^\s*#/d' -e '/^CONF_LINE/,/()/H' -e '/()/{x;s/.../\1/p;q}'`
```

- `sed` 在第 3 个表达式命中 `CONF_LINE: u_fopen_77()` 后**立即 `q` 退出**，管道读端关闭；
- 新版本 **clang（15.x）的 `-E` 预处理继续向管道写输出** → 触发 **SIGPIPE**
  （"write on a pipe with no reader"）；
- `_ax_icuio_UFOPEN` 取到空/错误值 → configure 报 "Failed to determine the true
  name of u_fopen" 中止。

这是 **autoconf-archive 宏自身的缺陷**（依赖 sed 先读完再退出的旧实现假设），
**非 OHOS 特有**——任何用 clang 编译且开启 AX_ICUIO 检查的 autotools 库都会踩中。

## 方案（fix_approach）

在配方 `build()` 内对 configure 脚本做**精确文本替换**，把该管道探测段整体替换为
硬编码真实符号名（跳过探测）：

```python
old = (
    "_ax_icuio_UFOPEN=`${CPP} ${CPPFLAGS} conftest.c | ${SED} "
    "-n -e '/^\\s*#/d' -e '/^CONF_LINE/,/()/H' "
    "-e '/()/{x;s/\\s*\\S\\+\\s\\+\\(\\w\\+\\).*/\\1/p;q}'` \\\n"
    "    || _ax_icuio_UFOPEN='error'"
)
configure = configure.replace(old, "_ax_icuio_UFOPEN='u_fopen_77'")
```

注意事项：

1. **两行反斜杠续行结构**：该段在 configure 中是
   `...` \\n `    || _ax_icuio_UFOPEN='error'` 两行，正则容易漏匹配，必须用精确
   多行字符串替换（首次用 regex 实现即失败，改为精确字符串后成功）。
2. **符号真名由 ICU 版本决定**（ICU 77 → `u_fopen_77`），可用
   `clang -E -I<icu-include> conftest.c` 实测确认（`CONF_LINE` 行输出即真名）。
3. **替换后链接探测仍需满足**：configure 继续做 `checking for u_fopen_77...`，
   该步要求 ICU 库可链接——**icu4c 静态 `.a` 是 C++ 库**，需在 LDFLAGS 注入 `-lc++`
   （`__gxx_personality_v0`/`__cxa_begin_catch`），否则链接检查仍失败。
4. **ICU I/O 依赖声明**：ohpcd 的 icu4c 包 `package_info` 只声明
   `pkg_config_name=icu-uc`，PkgConfigDeps 不生成 `icu-io.pc`，而 AX_ICUIO 需要
   `icu-io`/`icu` tag——需从 icu4c 包内复制 `icu-io.pc` 到 generators（pygobject
   `girepository-2.0.pc`、libgudev `libudev.pc` 同款 .pc 复制模式）。

**通用替代方案**（若库可改源码）：把 AX_ICUIO 的 sed 管道改为
`sed -n -e '/^CONF_LINE/{s/.*CONF_LINE: *//;s/(.*//;p;q;}'`（先取行再退出），
避免 SIGPIPE；或向 **autoconf-archive 上游提交 m4 修复**。

## 验证（verification）

cif-api 0.4.2 适配实测：

- patch 前：`checking the real name of u_fopen()... error: write on a pipe with
  no reader` + `configure: error: Failed to determine the true name of u_fopen`；
- 硬编码 `u_fopen_77` 后：`checking the real name of u_fopen()... u_fopen_77`；
- 注入 `-lc++` 后：`checking for u_fopen_77... yes`；
- `conan create cif-api/0.4.2` EXIT=0：`Package created`（libcif.so 构建），
  test_package 运行时真实执行 `cif-api OK (container created)`。

## 适用边界（applicable_to）

- 在 OHOS 上用 clang 构建、configure 含 AX_ICUIO 检查（ICU I/O）的 autotools 项目；
- 任何遇到 `${CPP} | sed ... q` 管道探测 SIGPIPE 的配置阶段失败场景。

## 不可适用情形（not_applicable_to）

- GCC 或其他不触发 SIGPIPE 的编译器（管道写端不被提前关闭，探测可正常完成）；
- ICU I/O 未被启用（`--without-icuio` 或库不调用 AX_ICUIO）的项目；
- 已修复该宏的上游 autoconf-archive 版本（需核对 m4 实现）。

## 查重（dedup）

查重范围：`knowledge/{doc,graph,drafts,index.tsv}`。

- SIGPIPE 关键词的既有条目为 **E106**（GNU coreutils cat stdout 权限受限导致
  configure SIGPIPE）——根因不同（E106=cat 写 stdout 权限/SELinux，本稿=sed `q`
  提前关闭管道读端），为 **similar_to 关系而非重复**；
- **AX_ICUIO / u_fopen / ICU I/O / autoconf-archive 宏缺陷**：现有 doc/graph/drafts
  中未见专条，为本稿新增价值核心；
- `knowledge/drafts/` 无同名/同 stem 草稿；本稿不占用正式 E 编号、不写
  `knowledge/doc`、`knowledge/graph` 或 `index.tsv`。

## 新增价值

- 定位并文档化 autoconf-archive `AX_ICUIO` 宏在 clang 下的**通用缺陷**（sed `q`
  提前关闭管道读端 → SIGPIPE），区别于既有 E106（cat 权限）根因；
- 给出配方级落地：精确多行字符串替换（反斜杠续行结构）+ 符号真名实测 +
  `-lc++` 静态链接注入 + `icu-io.pc` 复制，形成一套可复用的
  "AX_ICUIO 配置期失败"完整解法。
