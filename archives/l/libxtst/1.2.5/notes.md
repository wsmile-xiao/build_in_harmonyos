# libXtst / libxtst 1.2.5 适配笔记

## 边界

- 本任务只处理 `libxtst/1.2.5`（upstream libXtst 1.2.5，XTEST 扩展客户端库）。
- 目录：`archives/l/libxtst/1.2.5/`；Conan 包名沿用小写 `libxtst`（与 6.1.0 归档一致）。
- 版本策略：**上游版本直跟**（1.2.5），不沿用 6.1.0 的 ABI 版本方案（积分赛-依赖项任务要求）。
- 未修改 `libxtst/6.1.0` 及其他归档目录。

## 底稿与先例

- 底稿：`archives/l/libxtst/6.1.0/`（同库 ABI 版本包，2026-08-14 built，CI 验证通过）。
  autotools + X11 客户端库模式直接复用，只改版本与源 URL。
- 同族参考：`archives/l/libxau/1.0.12/`、`archives/l/libxext/1.3.7/`（上游版本策略先例）。
- 修复了 6.1.0 conanfile.py 中一处潜伏 bug：第一处 `_la_map` 替换循环里
  `_fp` 未定义即使用（触发时 NameError）；1.2.5 配方中改为先
  `_fp = os.path.join(_root, _fn)` 再写回。

## W0 依赖实测（2026-09-03，本机 conan 2.29.1 + ohpcd）

- `libx11/6.4.0`：RREV `63e25e48c3af73db324ce61d0dba9cce`，OHOS armv8 binary 下载 OK
- `libxext/6.4.0`：RREV `20942ab436730e84acb01dcf565fda68`，binary 下载 OK
- `libxi/6.1.0`：RREV `50ad8acc71529e01691678b59a9e0df6`，binary 下载 OK
- `libxfixes/6.1.0`：RREV `be822022a67fb63dc64824ec40d296ba`，binary 下载 OK
- `libxau/1.0.11`：RREV `e70832a1f31a85a0398300bf72179ad9`，本地缓存可用
- `xorgproto/2025.1`：RREV `f5274e33759da898a6e8d87d7708d47c`，binary 下载 OK
- `conan install --requires=libxi/6.1.0 ... --build=never` 拉全链 exit=0
- 备注：`libxext/1.3.7`（上游版本策略先例）未发布到 ohpcd（仓内只有 6.4.0/6.4.0.1），
  `libxi` 也只有 6.1.0——因此依赖版本跟随 6.1.0 底稿的 6.x ABI 系已发布包，
  保证依赖链单一 libx11/6.4.0，避免双版本 libx11 冲突。

## 源码

- URL: `https://xorg.freedesktop.org/archive/individual/lib/libXtst-1.2.5.tar.xz`
  （releases 路径在 CI 有连接超时史，archive 路径与 6.1.0/libxi/libxfixes 先例一致）
- sha256: `b50d4c25b97009a744706c1039c598f4d8e64910c9fde381994e1cae235d9242`（本机实测）
- 构建系统：autotools（release tarball 自带 configure/Makefile.in，无需 autoreconf）
- `configure.ac`: `PKG_CHECK_MODULES(XTST, [x11 >= 1.6] [xext >= 1.0.99.4] xi [recordproto >= 1.13.99.1] [xextproto >= 7.0.99.3] inputproto)`
- 上游测试：源码无 `check_PROGRAMS`/`TESTS`——libXtst 无独立测试套件（X11 库惯例），
  `make check` 无可执行用例。

## test_package 补全说明

- 上游无测试 → 按 R34 自行补全：`test_package/test.c` 链接 libXtst 并以与
  `XTestQueryExtension` 真实签名一致的函数指针做符号验证；`XOpenDisplay(NULL)`
  可用时实际调用 API，鸿蒙无 X server 时回退符号验证（与 6.1.0 同款已验证模式）。
- CMake 消费者：`find_package(libxtst)` + `target_link_libraries(... libxtst::libxtst)`。

## 验证（本机 W3）

见 `reports/` 与 `.ci-result.json`（finish 生成）。
---

**编译结束**: 2026-09-03 18:13
**最终状态**: built
