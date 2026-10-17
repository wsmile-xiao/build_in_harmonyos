# libcroco 0.6.13

libcroco 是 GNOME 的独立 CSS2 解析与操作库，提供 `libcroco-0.6.so`。

## 官方来源

- 上游仓库：https://gitlab.gnome.org/GNOME/libcroco
- 官方发布 tarball：https://download.gnome.org/sources/libcroco/0.6/libcroco-0.6.13.tar.xz
- SHA-256：`767ec234ae7aa684695b3a735548224888132e063f92db585759b422570621d4`（与官方 .sha256sum 清单一致）

## OHOS 适配

- 构建系统：autotools（configure + make）；依赖 glib-2.0 与 libxml-2.0（PKG_CHECK_MODULES）。
- 配方使用官方 release tarball（含生成式 configure），无需 autogen 自举。
- 2018 版 `config.sub` 不认识 `aarch64-linux-ohos`，通过 `0001-config.sub-ohos.patch` 加入 `linux-ohos` 候选，recipe 显式传入 `--build/--host=aarch64-linux-ohos`（与 aalib 先例一致）。
- 静态链接默认；头文件安装于 `include/libcroco-0.6/libcroco`。

## 测试

- 上游测试：`tests/` 下 7 个独立 C 测试程序（test0–test6）+ 4 个 shell 脚本测试（test-prop-ident、test-unknown-at-rule、test-unknown-at-rule2、test-several-media），通过 `testctl run` 与参考输出 diff 核验。
- 消费者用例：`test_package/consumer.c`，通过公开 API `cr_stylesheet_new_from_buf` + `cr_stylesheet_parse` 解析 CSS。