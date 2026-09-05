# asterisk-tds 22.10.1 适配笔记

## 编译环境
- **构建系统**: autotools（Asterisk 全量 configure + make）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 8（沿用 asterisk-speex/pgsql 的 OHOS 移植补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/a/asterisk-tds/22.10.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub codeload tag 下载（downloads.asterisk.org
在 OHOS 沙箱 404，codeload 实测可用）。

### 2. 依赖注入（generate()）
- `freetds/1.4.23` 提供 sybdb.h + libsybdb.a（静态，无 .pc/工具——TDS 模块链接目标）
- libedit/libxml2/ncurses/e2fsprogs/jansson/sqlite3 为 Asterisk 主 configure
  与 menuselect 子 configure 的硬要求（沿用 asterisk-pgsql 注入方式）
- **无需工具 shim**：asterisk configure 用
  `AST_EXT_LIB_CHECK([FREETDS], [sybdb], [dbinit], [sybdb.h])` 探测——
  靠 CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH 找到头与库即可

### 3. 构建（build()）
- 全量 configure（FREETDS 探测靠 CPPFLAGS/LDFLAGS 命中 sybdb.h/libsybdb.a，
  menuselect 启用 cdr_tds/cel_tds）
- 注入 packaging/menuselect.makedeps（声明 TDS 依赖），不覆盖 configure 生成的
  makeopts——让 configure 自然把目标模块标记为启用（含模块自符号）
- 只编译 cdr/cel 两个子目录的目标 .so（不依赖 asterisk 主程序）

### 4. 打包（package()）
- 产物 cdr_tds.so / cel_tds.so 到 `lib/asterisk/modules/`

## 依赖
- freetds/1.4.23（TDS 链接目标，ohpcd 已发布）+ Asterisk 主 configure 硬要求
  （libedit/libxml2/ncurses/e2fsprogs/jansson/sqlite3，均 ohpcd 已发布）

## 上游测试（rule 4）
- Asterisk 的 C 测试在 test/ 目录（main/ 各模块 test_*.c），tds 两模块
  （cdr_tds/cel_tds）**无专属上游测试**
  ——rule 1.2 如实声明"上游无测试"（非跳过）
- 本地验证：conan create 通过，两模块 .so 编译链接成功并打包
- 适配后：test_package R34 真实产物校验——两模块存在 + ELF shared
  object + 链接 FreeTDS/libsybdb，1/1 = 100%

## 已知限制
- 仅打包 tds 两模块，不包含 asterisk 主程序/其余模块
