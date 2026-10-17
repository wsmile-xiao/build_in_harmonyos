# harfbuzz 14.2.0.1 — Conan 配方笔记

- **版本**: **14.2.0.1**（R37：在已归档 `14.2.0` 上补齐 Conan 配方，配方内容与制品仓已发布的 `harfbuzz/14.2.0.1` 一致）
- **上游**: https://github.com/harfbuzz/harfbuzz/releases/download/14.2.0/harfbuzz-14.2.0.tar.xz
- **sha256**: `94017020f96d025bb66ae91574e4cf334bcad23e8175a8a40565b3721bc2eaff`
- **构建系统**: meson（MesonToolchain + PkgConfigDeps）
- **依赖**: glib/2.84.0.1、freetype/2.14.3、zlib/1.3.1.1
- **R38**: 软件级 `archives/h/harfbuzz/commands.json` 已登记 `14.2.0.1`（binary=true，hb-shape / hb-subset / hb-info）

## R37 合规说明

`harfbuzz/14.2.0.1` 已由 ohpcd 发布到制品仓（配方为早期版：无 graphite2、
`graphite2=disabled`、`system_libs` 不含 `c++`）。cnb.cool 制品仓不支持同版本多
revision 并存，故本配方必须与已发布版本逐字节一致（conanfile.py 归一化后对比、
conandata.yml 源码身份+patches 段对比均需 `same`），否则 CI L0j 判定
`version_not_incremented` FAIL。

含 graphite2 等改进的配方归入 `14.2.0.1.1`（已在 main，R37 版本号递增）。

## 关键配置（与已发布 14.2.0.1 一致）

- OHOS 上 `glib` 以 `shared=False` 静态链入（namespace.default.lib.paths 只允许
  libc.so / libc++_shared.so，dlopen /storage/.../*.so 报 EPERM），测试可执行文件
  ELF NEEDED 不含 libglib-2.0.so / libintl.so。
- `gobject`：OHOS 强制 `disabled`（PkgConfigDeps 不发射 glib_mkenums 变量），
  其他平台保持 `enabled`。
- `utilities=enabled`（门控 test/subset、test/shape、test/vector 套件注册）；
  `cairo/icu/chafa/png/gpu_demo` 均 disabled。
- `_inject_static_glib_intl()`：向生成的 glib-2.0.pc `Libs:` 追加绝对路径
  `libintl.a`（E107/E123，避免 `undefined g_libintl_*`）。
- `_sign_shared_libs()`：meson install 重写 rpath 后按 BINARY_SIGN_TOOL /
  user.ohos conf / Conan clang 同目录 / PATH 顺序解析绝对路径重新签名。

## 测试

- `tests=enabled`：build() 内执行上游 `meson test`。
- test_package 消费者：`hb_version_string()` / `hb_buffer_create()` API 冒烟，
  断言版本字符串含 `14.2.0.1`。

## 构建命令

```bash
conan create archives/h/harfbuzz/14.2.0.1 \
  --profile:host=<绝对路径>/ci/conan/profiles/ohos-aarch64 --build=missing
```
