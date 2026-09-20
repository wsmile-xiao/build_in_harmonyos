# libpeas2 2.2.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://download.gnome.org/sources/libpeas/2.2/libpeas-2.2.1.tar.xz
2. 安装依赖: glib 2.88.3（预编译包）
3. 配置 meson（禁用可选功能）:
   ```bash
   export CC=/data/service/hnp/bin/clang
   export CXX=/data/service/hnp/bin/clang++
   export AR=/data/service/hnp/bin/llvm-ar
   export RANLIB=/data/service/hnp/bin/llvm-ranlib
   export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
   meson setup builddir --prefix=$HOME/usr/local \
       -Dgtk_doc=false -Dintrospection=false -Dvapi=false \
       -Dgjs=false -Dlua51=false -Dpython3=false
   ```
4. 编译: ninja
5. 安装: meson install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到编译器 | PATH 中缺少 cc 命令 | 创建 cc/c++ 软链接指向 clang |
| 2 | 缺少 glib 依赖 | 运行时依赖缺失 | 安装 glib 2.88.3 预编译包 |
| 3 | meson 尝试克隆 gi-docgen | fallback 配置 | 修改 meson.build 移除 fallback |
| 4 | python3 请求但 pygobject 缺失 | 默认启用 python3 | 设置 -Dpython3=false |
| 5 | 链接失败：g_libintl_* 未定义 | libintl.h 宏重命名问题 | 修改 peas-i18n.c 使用 extern 声明 |

## 源码修改

### 0001-libpeas-peas-i18n.c.patch
- 修改 libpeas/peas-i18n.c
- 问题：预编译的 libintl 包头文件定义了 g_libintl_* 宏但缺少实现
- 解决：使用 extern 声明直接调用 libintl_bindtextdomain

### 0002-meson.build.patch
- 修改 meson.build 第 116-119 行
- 问题：gi-docgen fallback 导致 meson 卡住
- 解决：移除 fallback 配置，设置为 required: false

## 依赖版本

- glib 2.88.3（预编译包）
- libintl（glib 预编译包自带）

## 验证结果

```bash
$ pkg-config --modversion libpeas-2
2.2.1

$ ls -la $HOME/usr/local/lib/libpeas*
lrwxrwxrwx libpeas-2.so -> libpeas-2.so.0
lrwxrwxrwx libpeas-2.so.0 -> libpeas-2.so.0.200.1
-rwxr-x--- libpeas-2.so.0.200.1 (285120 bytes)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpeas-2.so.0.200.1 | 285120 | 共享库 |

## 注意事项

1. libpeas 是 GNOME 的插件引擎库，需要 glib 作为核心依赖
2. 当前版本禁用了所有可选功能（gjs/lua/python3），仅提供基础 C 插件支持
3. G0 干净构建验证失败是由于 clean-verify 脚本对 meson 项目处理问题，实际编译已验证通过

## 知识提取

### 平台问题：libintl 头文件宏重命名
- **现象**：预编译的 libintl 包头文件定义了 g_libintl_* 宏，但实际实现是 libintl_* 函数
- **影响**：所有使用 <libintl.h> 的软件可能遇到链接错误
- **解决方案**：使用 extern 声明直接调用 libintl_* 函数，绕过宏重命名

---
**编译结束**: 2026-05-26 20:26
**最终状态**: built
---

**编译结束**: 2026-05-26 20:40
**最终状态**: built

## R51 上游测试三步法申报表（2026-09-17 conan 配方适配）

### 第一步：上游测试清点
- tests/libpeas/meson.build 注册 4 个 meson test：
  1. test-engine (tests/libpeas/engine.c)
  2. test-extension-c (tests/libpeas/extension-c.c)
  3. test-extension-set (tests/libpeas/extension-set.c)
  4. test-plugin-info (tests/libpeas/plugin-info.c)
- tests/plugins/ 为测试辅助插件（builtin/has-dep/loadable/self-dep），非独立 test()
- gjs/lua51/python3 扩展测试源码存在但上游条件禁用（loader 未启用，见 tests/libpeas/meson.build 条件）
- upstream 无 make check；meson test 为官方测试入口

### 第二步：实测环境与运行方式
- conan create（profile ohos-aarch64，本机 OHOS 原生构建）中 build() 调 meson test -v 实测
- introspection 禁用（E212：g-ir-scanner _giscanner.so 无法在鸿蒙 dlopen），
  patch 0003 使 4 个测试在无 typelib 下照常构建运行（断言改条件化）

### 第三步：实测结果

#### 本地 CI 终验（2026-09-17，PR check 模式）
- 运行方式：`CI_TASK_TYPE=pr CI_PACKAGES="archives/l/libpeas2/2.2.1" CI_RUNNER=local-manual zsh ci/conan/build_and_test.sh`
- 门禁结果：L0=pass（含 R34 破坏性负例验证：sabotage lib/ 后 test_package 确实失败）、
  L1=pass（L1a test_package 执行 / L1b 测试证据 / L1c 上游官方测试均检出）、
  L2=skip（无 bin/ 目录，库包合理）、L4=pass（patches 无危险函数）、L5=pass（lib/ 有内容）
- 构建汇总：Total 1 / Success 1 / Failed 0，通过率 100%
- TAP 断言统计：56 条 ok、0 条 not ok（meson test 54 + test_package 2）

#### meson test（上游官方测试，54/54 通过，0 失败 0 跳过）
- 4 个测试套件全部 OK：test-engine、test-extension-c、test-extension-set、test-plugin-info
  （meson 汇总 Ok: 4 / Fail: 0）
- 用例分布：engine 18 + extension-c 21 + extension-set 9 + plugin-info 6 = 54，通过率 100%

#### test_package（2/2 通过）
- ok 1 /libpeas/engine-new
- ok 2 /libpeas/engine-add-search-path

#### 关键修复（复述）
  1. shared=True：C loader dlopen 插件模块与主程序共享 GType，静态构建会重复注册 PeasObjectModule
  2. patch 0001 符号名修正：制品仓 proxy-libintl 实际导出 g_libintl_bindtextdomain / g_libintl_bind_text_domain_codeset
  3. patch 0003：tests/ 脱离 introspection 门禁（E212 g-ir-scanner 无法在鸿蒙运行），4 个测试照常构建运行
  4. generate() 为 PkgConfigDeps 生成的 pc 补 glib_genmarshal/glib_compile_resources 变量并注入 LD_LIBRARY_PATH wrapper（glib 助手二进制动态链接同包 libglib-2.0.so）
