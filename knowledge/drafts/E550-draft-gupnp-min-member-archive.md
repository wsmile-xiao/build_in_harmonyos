# E550（draft）— 最小补链归档：消费者调用中间共享库未导出的依赖 API

- **来源**: gupnp 1.6.10 HarmonyOS PC 适配
- **状态**: draft（待审，勿自行 promote）
- **关联**: 前置架构见 GLib 栈 GObject 单副本教义（gssdp 1.6.6 适配确立：
  静态 glib 的 Libs 全部剔出链接、g_* 全 UND、运行时解析到 libsoup-3.0.so
  导出的唯一 gobject 副本）

## 1. 现象

按单副本教义剔空 GLib 系 .pc 的 Libs 后，libgupnp-1.6.so 链接报两个未解析
符号（meson 对 shared library 默认 `-Wl,--no-undefined`）：

```
ld.lld: error: undefined symbol: g_uuid_string_random   # gupnp-service.c SID 生成
ld.lld: error: undefined symbol: g_zlib_compressor_new  # http-headers.c gzip 压缩体
```

而 libsoup-3.0.so 的 dynsym 实测导出 4121 个 `g_*` 符号，**不含**这两个：
libsoup 只导出它自己引用的 glib 符号。"中间 .so 导出完整依赖符号表"在
gssdp 场景成立，对 gupnp 的这两个调用点不成立。

## 2. 两个失败方案（实测对照）

| 方案 | 结果 |
| --- | --- |
| 把 `-lglib-2.0 -lgio-2.0` 加回 glib-2.0.pc 的 Libs（整档归档按需拉取） | ld 级联拉取失控：libgupnp 定义符号 3812 个，glib/gio 大面积复制（弃用） |
| 去掉 `-Wl,--no-undefined` 保持全 UND | 运行时 g_uuid_string_random 无任何已加载库可解析 → 加载期失败（且是砍安全检查，不采纳） |

## 3. 修法：最小成员补链归档

```sh
ar x $GLIB2_PKG/lib/libglib-2.0.a guuid.c.o          # g_uuid_string_*
ar x $GLIB2_PKG/lib/libgio-2.0.a  gzlibcompressor.c.o # g_zlib_compressor_*
ar qc libglib-min.a guuid.c.o gzlibcompressor.c.o
```

配方在 `generate()` 里构建该归档，并让 PkgConfigDeps 生成的 `glib-2.0.pc`
的 Libs 指向它（`-L<dir> -lglib-min`）——meson/测试链接自然带上。

**约束（必做）**：
1. 对每个成员 `nm -u` 全量核对：其未解析符号必须全部能被中间共享库导出表
   或链接行上已有的库满足。实测两成员全部 `g_type_*`/`g_object_*` 引用均被
   libsoup 导出满足 → GObject 单副本不破坏（GZlibCompressor 的 get_type
   只是把类型注册进 libsoup 持有的唯一类型系统，懒注册）。
2. 产物画像复核：`readelf --dyn-syms`——libgupnp 定义符号 257 个，`g_*`
   仅 8 个（= 两成员自身函数），`g_type_*`/`g_object_*` 定义 0 个。

## 4. 验证证据（gupnp 1.6.10）

- 链接通过（`-Wl,--no-undefined` 保持开启）；
- 打包产物 `sha256 == 构建树产物`（1fdd4d14…，字节一致）；dlopen 成功；
- `meson test` 7 程序 56 TAP 子用例全过、test_package 14 项断言过——若
  GObject 多副本撕裂（`g_type_register_static` assertion SIGABRT）会立即
  暴露（gssdp 历史铁证），实测未发生；
- 全部证据见 `reports/conan-verify-supplement.md`。

## 5. 适用面与边界

- **适用**: GLib 栈后续包（gupnp-av、gupnp-dlna、rygel…）在"静态 glib 单副本
  经 libsoup-3.0.so 间接提供"布局下调用 libsoup 未导出的 glib/gio API；
  泛化为任何"静态依赖经中间共享库间接提供符号"的链接布局。
- **不适用**: 成员 UND 闭包拉入类型系统定义（说明该 API 深度耦合 gobject，
  应转向整链共享化——需 ohpcd 发布 shared glib2 + libsoup3 重建，另立任务）；
  缺失符号多而分散（维护成本超过收益）。
