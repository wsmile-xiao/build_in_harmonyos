# E322: out-of-source 构建 install-data-am 的 $(EXTRA_DIST) 相对路径找不到源文件

> **Contributor**: 672C | **Status**: Draft | **Updated**: 2026-08-28
> **Severity**: 2 | **Category**: autotools / packaging / conan

## 错误特征

Autotools 项目自定义 `install-data-am` 规则安装源码目录文件，conan
out-of-source 构建（build-release 子目录）时报：

```text
/storage/Users/currentUser/usr/local/bin/ginstall -c -m 644 vars-pl.txt  .../share/ekg2/plugins/logs/
ginstall: cannot stat 'vars-pl.txt': No such file or directory
make[3]: *** [Makefile:745: install-data-am] Error 1
```

## 触发条件

- 构建系统: autotools（自定义 install-data-am / install-exec-hook 规则）
- 阶段: make install（package() 内 autotools.install()）
- 平台: 所有（conan 默认 out-of-source 构建时普遍触发）

## 根因分析

1. conan 默认 **out-of-source 构建**：源码在 `source_folder`，构建在
   `build-release/` 子目录，Makefile 在 build 目录执行。
2. `install-data-am` 直接用 `$(EXTRA_DIST)`（如 `vars-pl.txt`）安装文件，
   相对路径从 **build 目录**解析，找不到源码目录里的文件。
3. 涉及文件：`EXTRA_DIST` 列表、`$(DOCS)` 变量、`themes/*` glob 等
   （egk2 有 20+ 个插件的 Makefile.am 同类问题）。

## 解决方案

`install-data-am` 中安装源码目录文件时加 `$(srcdir)/` 前缀：

```makefile
install-data-am:
	mkdir -p $(DESTDIR)$(pkgdatadir)/plugins/logs/
	$(INSTALL) -m 644 $(addprefix $(srcdir)/,$(EXTRA_DIST)) \
		$(DESTDIR)$(pkgdatadir)/plugins/logs/
```

变体处理：
- `${EXTRA_DIST}`（花括号）：`$(addprefix $(srcdir)/,${EXTRA_DIST})`
- `$(EXTRA_DIST_DOC)` / `$(DOCS)`：同样加 `$(addprefix $(srcdir)/,...)`
- `themes/*` glob：`$(addprefix $(srcdir)/,themes/*)`

注意 `.am` 是源码，修改后需重新 `autoreconf -fi` 生成 Makefile.in；
用 refresh-patch 固化为补丁（每个插件的 Makefile.am 一个 patch）。

## 验证

```bash
conan create archives/e/ekg2/0.3.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# → make install 无 cannot stat 错误，所有插件文件正常安装
```

## 关联条目

- 相关: E041（autotools VPATH/out-of-source 构建）
