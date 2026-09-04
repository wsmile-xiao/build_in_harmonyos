# asterisk-curl 22.10.1 适配笔记

## 编译环境
- **构建系统**: autotools（Asterisk 全量 configure + make）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 8（沿用 asterisk-speex/pgsql 的 OHOS 移植补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/a/asterisk-curl/22.10.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub codeload tag 下载（downloads.asterisk.org
在 OHOS 沙箱 404，codeload 实测可用）。

### 2. 依赖注入（generate()）
- `libcurl/8.5.0` 提供 curl/curl.h + libcurl.so + libcurl.pc + curl-config
  （curl 模块链接目标）
- libedit/libxml2/ncurses/e2fsprogs/jansson/sqlite3 为 Asterisk 主 configure
  与 menuselect 子 configure 的硬要求（沿用 asterisk-pgsql 注入方式）
- **curl-config**：libcurl 包自带 curl-config 二进制，`_ensure_dep_present`
  复制到私有 prefix/bin，configure 用 `AC_PATH_TOOL` 探测（--with-curl 指向
  prefix）；若包内缺失则以 shim 兜底（--cflags/--libs 报 prefix 路径）

### 3. 构建（build()）
- 全量 configure（--with-curl=<prefix> 使 AST_EXT_LIB_CHECK CURL 通过，
  menuselect 启用 res_curl/func_curl/res_config_curl）
- menuselect 注入 packaging/menuselect.makeopts（排除语义：除三模块全禁用）
- 只编译 res/funcs 三个子目录的目标 .so（不依赖 asterisk 主程序）

### 4. 打包（package()）
- 产物 res_curl.so / func_curl.so / res_config_curl.so
  到 `lib/asterisk/modules/`

## 依赖
- libcurl/8.5.0（curl 链接目标，ohpcd 已发布）+ Asterisk 主 configure 硬要求
  （libedit/libxml2/ncurses/e2fsprogs/jansson/sqlite3，均 ohpcd 已发布）

## 上游测试（rule 4）
- Asterisk 的 C 测试在 test/ 目录（main/ 各模块 test_*.c），curl 三模块
  （res_curl/func_curl/res_config_curl）**无专属上游测试**
  ——rule 1.2 如实声明"上游无测试"（非跳过）
- 本地验证：conan create 通过，三模块 .so 编译链接成功并打包
- 适配后：test_package R34 真实产物校验——三模块存在 + ELF shared
  object + 链接 libcurl，1/1 = 100%

## 已知限制
- 仅打包 curl 三模块，不包含 asterisk 主程序/其余模块
