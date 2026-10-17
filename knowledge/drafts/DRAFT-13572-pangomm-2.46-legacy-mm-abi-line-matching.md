# DRAFT-13572-pangomm-2.46-legacy-mm-abi-line-matching：GNOME C++ 绑定家族双 ABI 线的识别与依赖版本匹配

> Contributor: LIMInGZE666 | Status: Draft | Updated: 2026-09-27
> Source: pangomm-2.46 2.46.5 适配（任务 13572）
> 对应：`knowledge/drafts/DRAFT-13572-pangomm-2.46-legacy-mm-abi-line-matching.kv`

## 问题

gtkmm 生态的 C++ 绑定家族（glibmm / cairomm / pangomm / atkmm / gtkmm）
**双 ABI 线并行发布**，两线平行可装、互不兼容，且旧线至今仍在发维护版：

| 家族 | 旧 ABI 线（pc 名） | 版本号范围 | 新 ABI 线（pc 名） | 版本号范围 |
|------|--------------------|-----------|--------------------|-----------|
| pangomm | pangomm-1.4 | 2.46.x 封顶 | pangomm-2.48 / 2.50 / 2.56 | 2.48+ |
| glibmm | glibmm-2.4 / giomm-2.4 | 2.66.x | glibmm-2.68 / giomm-2.68 | 2.68+ |
| cairomm | cairomm-1.0 | 1.14.x | cairomm-1.16 | 1.16+ |

**核心陷阱：版本号高低与 ABI 线新旧没有一一对应。** glibmm 2.66.9 是旧线
（configure.ac 里 `MM_INIT_MODULE([glibmm-2.4])`，生成的 pc 叫 glibmm-2.4.pc）；
而 pangomm 2.46.5 2026-06-25 还在发维护版，它依赖的是旧线
`glibmm-2.4 >= 2.48.0`。若按「同族选最新已适配版本」惯性拿 glibmm/2.68.2
（生成 glibmm-2.68.pc），meson 的 `dependency('glibmm-2.4')` 直接
configure 失败——本赛制下任务 13756 的同款 MR 两次 CI 挂掉与此吻合。

## 识别：tarball 内三件套取证

```sh
tar xJf pangomm-2.46.5.tar.xz
# ① autotools 线：pc 名真身在 configure.ac 的 MM_INIT_MODULE
grep -n "MM_INIT_MODULE" glibmm-2.66.9/configure.ac     # → [glibmm-2.4] [giomm-2.4]
# ② meson 线：api_version + pcname
grep -n "api_version\|pcname" pangomm-2.46.5/meson.build
#    → pangomm_api_version = '1.4'；pangomm_pcname = pangomm-1.4
# ③ 版本系列归属看 NEWS（2.46.5 标注 legacy 维护）
```

然后用 `dependency('X')` 里的 **X 精确字符串（pc 名）** 去 repo 的 archives/
反查哪个版本生成同名 .pc：

| pangomm 2.46.5 需求 | repo 侧匹配 | 判定依据 |
|---------------------|------------|---------|
| glibmm-2.4 >= 2.48.0 | glibmm/2.66.9 | 组件 `pkg_config_name = "glibmm-2.4"`（上游 MM_INIT_MODULE 一致），2.66.9 >= 2.48.0 |
| cairomm-1.0 >= 1.2.2 | cairomm/1.14.5.1 | `pkg_config_name = "cairomm-1.0"`，ABI 系列 <=1.14.z |
| pangocairo >= 1.45.1 | pango/1.56.4 | 版本达标（pangocairo 转发 pc 另见 gap-trio 草稿） |

**逐字节比对**：需求方 meson 的 dependency() 字符串 vs 供给方配方的
`pkg_config_name`，一致才算匹配；版本号比较只是第二道过滤。

## 适配口径

1. **先定 ABI 线再选依赖**——禁止按同族最新版本惯性；
2. **repo 有同族模板就照搬机制、只换 ABI 标识**：pangomm/2.50.1（新线）
   模板全套机制（alias-pc / pc-var / libdir 注入 / codesign）对 2.46.5 照抄，
   替换点为：包名（任务卡 pangomm-2.46）、pc 名（pangomm-1.4）、头布局
   （include/pangomm-1.4 + lib/pangomm-1.4/include）、链接名
   （-lpangomm-1.4 -lcairomm-1.0 -lglibmm-2.4 -lsigc-2.0）、gmmprocdir 值
   （${libdir}/glibmm-2.4/proc）、extra_defs 工具库
   （glibmm_generate_extra_defs-2.4）；
3. **旧线栈的钉版冲突用 override 对齐**：glibmm/2.66.9 钉 libsigc/2.10.8、
   cairomm/1.14.5.1 钉 libsigc/2.12.1 → `self.requires("libsigc/2.12.1",
   override=True)`（sigc++-2.0 在 2.x 内 SONAME libsigc-2.0.so.0 不变，安全）；
4. **禁止 sed 改上游 pc 名**：ABI 线不兼容是符号表层面，改名救不了链接。

## 跨库适用

- gtkmm-2.4 / gtkmm-3.0 = 旧线栈（glibmm-2.4 + cairomm-1.0 + pangomm-1.4）；
- gtkmm-4.0 = 新线栈（glibmm-2.68 + cairomm-1.16 + pangomm-2.48）；
- 未来任何 gtkmm 生态任务的依赖选型，先跑一遍本三件套。
