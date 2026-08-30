# ekg2 0.3.1 编译笔记（HarmonyOS PC · Autotools）

## 定位
- ekg2 是一个多协议、多 UI 的即时通讯客户端（Jabber/XMPP、GG、IRC 等）
- 提供 ncurses 控制台 UI 和 GTK2 GUI，插件化架构（30+ 插件）
- **适配结果：conan-verify 全绿（G1-G4 + L2/L4/L5），`ekg2 --help` 运行成功**

## 最终依赖（全部已发布在 ohpcd）
- ✅ ncurses/6.6（控制台 UI）
- ✅ expat/2.8.2.1.1（XML 解析）
- ✅ zlib/1.3.1.1（压缩，与 python 依赖链一致）
- ✅ readline/8.3（命令行编辑）
- ✅ sqlite3/3.49.1（数据库日志）
- ✅ gnutls/3.8.10（TLS）
- ✅ aspell/0.60.8（拼写检查）
- ✅ libjpeg/10（JPEG 图片）
- ❌ openssl（sim 插件用 OpenSSL 1.0 API，OHOS 只有 1.1+，禁用）
- ❌ perl/python（脚本插件需 XS 编译，OHOS 工具链不支持，禁用）

## 构建系统
- Autotools：GitHub tag tarball **不带 configure**，build() 用 `autoreconf -fi` 生成
- tool_requires: automake/1.18 + libtool/2.5.4 + pkgconf/3.0.5

## 适配中的坑（按出现顺序）

### 1. 依赖版本冲突（openssl/zlib）
- ekg2 原配方用 openssl/3.5.6.1.1 + zlib/1.3.2，与 python/3.12.9 配方的
  openssl/1.1.1w + zlib/1.3.1.1 冲突
- 解法：ekg2 降到与 python 链一致（openssl/1.1.1w、zlib/1.3.1.1）

### 2. automake 版本
- 原配方 automake/1.18.1 不在制品仓（只有 1.18），pkgconf 2.4.3 → 3.0.5

### 3. gettextize/autopoint 不可用（关键）
- autogen.sh 需要 gettextize/autopoint，制品仓 gettext 包（0.22.5.1）无工具或
  autopoint 硬编码 `prefix="/"` 找不到数据文件
- 解法：patch 掉 configure.ac 的 `AM_GNU_GETTEXT`/`AM_GNU_GETTEXT_VERSION` 宏 +
  po/ 子目录（Makefile.am SUBDIRS + AC_CONFIG_FILES），彻底绕开 gettext
- 附带：automake 需要 ChangeLog 文件 → patch 新增空 ChangeLog

### 4. gettext tool_require 拉 perl 污染
- 曾加 gettext/0.22.5.1 tool_require，其 host 依赖 perl 把 XS 模块注入 PATH，
  导致系统 autom4te/autoreconf 加载 conan perl 的 IO.so/Cwd.so 失败
- 解法：移除 gettext tool_require，改用 autoreconf -fi（opendmarc 同款）

### 5. E007 三元组（cannot run C compiled programs）
- 第一次写 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  → build==host，configure 认为非交叉编译，尝试运行目标二进制失败
- 正确：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
  （build 用 gnu，host 用 ohos，configure 识别为交叉编译）

### 6. libtool .la 坏路径（新坑）
- OHOS conan autotools 包用 --prefix=/ 安装，.la 里 `libdir='//lib'`，
  dependency_libs 引用 `//lib/xxx.la`，libtool 链接插件时
  "is not a valid libtool archive"
- 解法：build() 里 `_fix_la_libdirs()` 遍历所有 host 依赖，把 `//lib` 修正为
  依赖包实际 lib 目录（先收集全图映射，再逐个替换）

### 7. sim 插件 OpenSSL API 不兼容
- simlite.c 用 OpenSSL 1.0 的 EVP_MD_CTX（opaque struct）→ OHOS 只有 1.1+
- 解法：`--without-openssl` 禁用 sim 插件（configure.ac 明确此选项）

### 8. musl 无 index()/rindex()（E006 类）
- xmalloc.c 的 xindex/xrindex 用 index()/rindex()，musl libc 无此符号
- 解法：patch 为 strchr()/strrchr()

### 9. 插件/文档 install 相对路径（新坑）
- 20 个插件 + docs + contrib 的 install-data-am 直接 install `$(EXTRA_DIST)`
  （或 `${EXTRA_DIST}`/`$(EXTRA_DIST_DOC)`/`themes/*`），out-of-source 构建
  （build-release 子目录）找不到源文件
- 解法：批量 patch 为 `$(addprefix $(srcdir)/,$(EXTRA_DIST))`

### 10. test_package 运行缺动态库
- gnutls 产物是 .so 但配方标 shared=False，VirtualRunEnv 不注入其 lib 路径
- 解法：test() 手动收集所有依赖 lib 目录注入 LD_LIBRARY_PATH
  （需跳过 package_folder 为 None 的 tool_requires）

### 11. conan patch 默认 strip=0（关键坑）
- refresh-patch 生成的 patch 是 `a/xxx b/xxx` 格式（Git 风格，需 -p1）
- conan 的 apply_conandata_patches 默认 strip=0 → 应用失败
- 解法：conandata.yml 每个 patch 条目必须加 `strip: 1`

### 12. refresh-patch 会重写 patches 目录（关键坑）
- finish 的 refresh-patch 步骤每次会重新生成 patches（从 build 目录对比 orig）
- 若 build 目录（work）被 autogen/configure 产物污染，会生成大量垃圾 patch（96 个）
- **解法**：work 目录必须保持"仅源码修改"状态；ChangeLog、musl 修复等
  不适合 patch 的改动放 conanfile build() 内联处理（refresh-patch 重排编号会覆盖）
- 顺序：先跑 refresh-patch 确认 patch 集合，再 commit；不要在 commit 后依赖
  refresh-patch 保持文件不变

### 13. W4 审计发现的提交前检查项
- commands.json 的 `binary` 必须与 manifest status 一致（built → false）
- conandata.yml 的 sources.url 必须保持官方 https URL（预下载缓存改写的
  file:// 路径不能提交，CI 干净环境拉取失败）
- manifest.yaml 的 dependencies/configure_options/patches_applied 必须与
  配方实际逐项对齐


## 测试
- `ekg2 --help`：✅ 输出完整帮助信息（含 -v/--version 等选项）

## 状态
**built** — conan-verify 全绿 + W4 审计通过，待 submit
---

**编译结束**: 2026-08-28 20:10
**最终状态**: built
