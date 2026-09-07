# DRAFT-ohos-autotools-maintainer-noregen — CI 无 autotools 工具链时禁用 maintainer 再生成

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-05 | Severity: 🟡 medium
> Source: libapparmor 5.0.0（PR #8292）CI conan create 失败链

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|---------|--------|--------------------------|
| DRAFT-6048（babeltrace） | draft | 同族：automake maintainer 规则 make 阶段重新运行 autoconf 覆盖 umask 替换；修法为时间戳设为 2000-01-01 | 本 skill 覆盖其未覆盖的**两个点**：①源码树无 configure 时用 conan `tool_requires("automake")` + `autoreconf` 自举（与 psfex/scamp 一致，不依赖宿主环境）；②Makefile 里 AUTOCONF 是 **AC_PATH_TOOL 固化的绝对路径**，PATH 前置 fake 无效，必须用 **make 命令行变量覆盖**（优先级最高） |
| E059 / E069 / E175 / E178 | 已收录 | 方向相反：用系统 automake/aclocal/autoreconf **重新生成** aclocal.m4/configure | 本 skill 是**不重新生成**（make 命令行变量覆盖 + 时间戳分层），针对"make 阶段被 maintainer 规则重新生成覆盖修复"的场景 |
| E011（umask 077） | 已收录 | HMDFS 下 config.status umask 077 不可写 | 依赖关系：本 skill 的 configure 同样需 umask 077→022，但本 skill 聚焦**防再生成**，两者互补 |

**撞车判定**：全库查证 `tool_requires.*automake.*autoreconf`（0 命中）、`make.*AUTOCONF.*绝对路径.*覆盖`（0 命中）、`touch -t 200101010000`（0 命中）。时间戳 trick 本身与 DRAFT-6048 重叠，但问题层（无工具链 CI + 绝对路径覆盖）不同，作为**姊妹条目**申报。

## Scope（何时用）

- autotools 老项目（gitlab archive 不含预生成 configure，需 autogen.sh 或手动 aclocal/autoconf/automake）
- CI worker **无 autotools 工具链**：`aclocal: inaccessible or not found`（uid 100 无法访问 usr/local/bin）或缺失 automake/aclocal
- 但 `autoconf` 存在且被 `AC_PATH_TOOL` 固化为 Makefile 变量绝对路径 → PATH fake 无效
- make **和** make install 阶段都会触发 maintainer 规则

## Symptom

```
/system/bin/sh: aclocal: inaccessible or not found
...
make[2]: *** [tests/CMakeFiles/gschemas-compiled.dir/build.make:73: ...] Error 1
...
CDPATH=... cd . && /data/service/hnp/bin/bash '.../missing' aclocal-1.16
 cd . && /data/service/hnp/bin/bash .../missing automake-1.16 --foreign
CDPATH=... cd . && /data/service/hnp/bin/autoconf
configure.ac:101: m4_ifndef([AX_CHECK_COMPILE_FLAG], [AC_MSG_ERROR(['autoconf-archive' missing])])
configure: error: 'autoconf-archive' missing
make: *** [Makefile:391: config.status] Error 1
```

## Root Cause

1. **autotools maintainer 规则**：automake 生成的 Makefile.in 在 `configure.ac`/`aclocal.m4`/`Makefile.am`/`m4/*.m4` 时间戳新于生成文件时，make 自动运行 aclocal → automake → autoconf 重新生成。
2. **工具链不对称**：CI worker 无 aclocal/automake（`missing aclocal-1.16` 返回 0 继续），但 **autoconf 存在**（`/data/service/hnp/bin/autoconf`）——configure 时 `AC_PATH_TOOL` 把它固化为 Makefile 的 `AUTOCONF` 绝对路径。
3. **坏 configure 覆盖**：autoconf 用（重新生成后宏缺失的）aclocal.m4 重跑，`m4_ifndef([AX_CHECK_COMPILE_FLAG])` 触发 `'autoconf-archive' missing`；若 aclocal 真正运行则会丢掉本地 m4/ 宏。
4. **PATH fake 无效**：Makefile 里 AUTOCONF 是绝对路径（绕过 PATH），ACLOCAL 经 `missing aclocal-1.16` 调用带版本号（fake 只建 `aclocal` 不匹配）。

## Recommended Solution

### 主方案：tool_requires 工具链 + autoreconf 自举 + make 命令行变量覆盖

1. **源码树无 configure 时用 conan tool_requires 工具链自举**（与 psfex/scamp/skymaker 一致，不依赖宿主环境的 aclocal/automake）：
   ```python
   def build_requirements(self):
       self.tool_requires("automake/1.18")
       self.tool_requires("libtool/2.5.4")
   # build():
   # 源码缺 m4 宏（ax_check_compile_flag.m4 / pkg.m4，autoconf-archive/pkg-config 宏），
   # 先写入 m4/ 再 autoreconf
   self._write_m4_macros(libdir)
   if not os.path.isfile(os.path.join(libdir, "configure")):
       self.run(f"cd {libdir} && autoreconf -fiv -I m4")   # -I m4：aclocal 默认不搜 m4/ 子目录
   ```
   - **PERL5LIB 覆盖陷阱**：conanbuildenv 生成的 `PERL5LIB` 是 `usr/local/share/automake-1.16:.../automake-1.18`（profile buildenv 的 1.16 在前），conan automake/1.18 会加载 1.16 模块报 `version mismatch. This is Automake 1.16.5 ... comes from Automake 1.18`。`self.run` 内部会重载 conanbuildenv 覆盖 os.environ，且 `self.dependencies` 取不到 tool_requires 包——需在命令内用 `$AUTOMAKE`（conanbuildenv 已 export）推算包内 share 并内联 PERL5LIB 前缀：
     ```sh
     AM_PFX=$(dirname $(dirname "$AUTOMAKE")) && PERL5LIB="$AM_PFX/share/automake-1.18" autoreconf -fiv -I m4
     ```
   - **m4 宏缺失**：`configure.ac` 的 `m4_ifndef([AX_CHECK_COMPILE_FLAG], [AC_MSG_ERROR(['autoconf-archive' missing])])` 要求宏定义，源码树未带 autoconf-archive/pkg-config 宏，build() 先写入 `m4/ax_check_compile_flag.m4` + `m4/pkg.m4` 再 autoreconf。

2. **make 命令行变量覆盖**（防 make 阶段 maintainer 规则重新生成覆盖修复）：Makefile 里 AUTOCONF 是绝对路径（AC_PATH_TOOL 固化），PATH fake 无效，用 **make 命令行变量**（优先级最高）：
   ```python
   self.run(f"cd {libdir} && make -j1 "
            f"AUTOCONF={fakebin}/autoconf ACLOCAL={fakebin}/aclocal "
            f"AUTOMAKE={fakebin}/automake AUTOHEADER={fakebin}/autoheader "
            f"LIBTOOLIZE={fakebin}/libtoolize")
   ```
   package() 的 `make install DESTDIR=...` 需同样覆盖。
3. **config.guess/config.sub OHOS 识别**：autoreconf 生成的 config.guess/config.sub 不含 HarmonyOS 分支，`_patch_ohos_autotools()` 内联补 `__OHOS__`/`HarmonyOS`/`ohos-linux` 识别（同 psfex/scamp）。
4. **时间戳分层**（防 make 判定 configure 过期触发 `config.status --recheck`）：源文件设 2000-01-01、预生成文件设 2001-01-01、configure 产物保持当前。

> 注：曾尝试 `autogen-output/` 预置生成文件（本机 autogen 产物随 exports_sources 携带）方案，因 23 个生成文件使 PR diff 庞大且未复用仓库既有的 tool_requires 成熟方案，最终改为上述 tool_requires+autoreconf 方案（与 psfex/scamp/skymaker 对齐）。

### 回退方案

- configure.ac 若启用 `AM_MAINTAINER_MODE`：`./configure --disable-maintainer-mode`（libapparmor 5.0.0 实测不支持）。

### 禁止

- `PATH=<fakebin>:$PATH make`：AUTOCONF 是绝对路径，fake 不生效。
- 把预生成文件 touch 为当前时间：config.status/Makefile（configure 产物）会早于 configure → make 触发 `config.status --recheck` → 重跑 configure 报错。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| libapparmor 5.0.0 | 本 skill 来源 | 覆盖前：CI conan create 多次失败（aclocal inaccessible → ar-lib → Makefile.in 缺失 → autoconf-archive missing）；覆盖后：conan-verify 全门禁 PASS（G0-G5/L2/L4/L5） |

## 测试覆盖边界

- 通过率口径：conan create/make/make install/test_package 全链通过；test_package 1/1。
- 未覆盖：无 autoconf 的场景（本方案仍依赖 configure 脚本存在，只是不再重新生成）。
