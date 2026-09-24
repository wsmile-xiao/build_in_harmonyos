# E664-autotools-config-script-deps-need-explicit-prefix：config 脚本型依赖发现不吃 AutotoolsDeps 注入，需显式 `--with-<lib>=<conan 包目录>`

> Contributor: lnav-0.13.2 任务 | Status: Draft | Updated: 2026-09-22
> Source: lnav 0.13.2 适配（feat/lnav-0.13.2）
> 对应：`knowledge/drafts/E664-autotools-config-script-deps-need-explicit-prefix.kv`

## 现象

conan 依赖图里明明有 curl/pcre2/sqlite3（`AutotoolsDeps` 也生成了 `-I/-L/-l`），
configure 阶段仍然报：

```console
checking for curl... no
configure: error: libcurl required to build
# 或
configure: error: either specify a valid PCRE2 installation with
--with-pcre2=DIR or disable PCRE2 usage with --without-pcre2
# 或
checking for curl-config... no
```

## 根因

autotools 的依赖发现有两族，注入通道**完全不同**：

| 族 | 典型宏 | 吃什么 |
|---|---|---|
| 库探测 | `AC_CHECK_LIB` / `AC_SEARCH_LIBS` / `AC_CHECK_HEADERS` | 编译器环境变量 → AutotoolsDeps 的 CPPFLAGS/LDFLAGS/LIBS **直接覆盖** |
| config 脚本/系统目录 | `LIBCURL_CHECK_CONFIG`（curl-config）、`AX_CHECK_PCRE2`、pkg-config 形态 | `AC_PATH_PROG` 沿 **PATH** 找脚本；`AX_CHECK_PCRE2` 默认 places 是**字面系统目录** `/usr/local /usr /opt/local /sw` |

conan host 依赖的 `bin/` 不在 conanbuild 的 PATH 里（那是 tool_requires 的
build 工具链通道），conan 包目录也不在宏默认的系统目录清单里 → 机器上有依赖、
configure 依然找不到；更糟的变体是扫到宿主系统同名库形成静默错配。

同族但不同根因：conan 包内的 config 脚本自带**构建期陈旧 prefix**（xml2-config
家族，见 DRAFT-ohos-libxml2-xml2-config-prefix-stale）——那条是"找到了但路径错"，
本条是"宏的发现通道根本够不到 conan 包"。

## 修法（推荐）

generate() 里用依赖的 `package_folder` 组装显式宏参数：

```python
tc.configure_args.append(
    f"--with-libcurl={self.dependencies['curl/8.15.0.1'].package_folder}")
tc.configure_args.append(
    f"--with-pcre2={self.dependencies['pcre2/10.48'].package_folder}")
```

- `LIBCURL_CHECK_CONFIG`：`AC_PATH_PROG` 先查 `$withval/bin`，一次命中；
- `AX_CHECK_PCRE2`：withval 目录被插到搜索链最前，循环在
  `include/pcre2.h` 命中即停；
- 同时建议 `--disable-system-paths` 关掉 `/opt/local`、`/usr/local` 兜底扫描，
  依赖只可能命中 conan 那一份（R49/E524 共享前缀禁令精神）。

## 兜底

把依赖包 `bin/` 前置到构建 env PATH（`env.append_path("PATH", ...)`）让
`AC_PATH_PROG` 命中——但包内脚本 prefix 陈旧时输出仍是错路径，需校验。

## 禁止

- `ac_cv_lib_xxx=yes` 硬灌 cache 变量绕过探测（跳过验证 = 假绿通道）；
- `-I/usr/include`/`-L/usr/local/lib` 注入系统前缀（R49/E524）。

## 复现/验证

```console
grep -n 'LIBCURL_CHECK_CONFIG\|AX_CHECK_PCRE2' <包>/configure.ac
# 构建日志应出现 checking for curl... <conan 包路径>（而非系统目录）
```
