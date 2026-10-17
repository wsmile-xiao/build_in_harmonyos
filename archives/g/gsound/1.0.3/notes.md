# gsound 1.0.3 适配笔记

## 上游信息

- 上游仓库：https://gitlab.gnome.org/GNOME/gsound
- 源码包：https://download.gnome.org/sources/gsound/1.0/gsound-1.0.3.tar.xz
- 版本：1.0.3
- 许可证：LGPL-2.1-or-later
- 构建系统：meson + ninja

## 上游测试清点

gsound 1.0.3 源码包中**无自动化测试套件**：

- 无 `tests/` 目录
- 无 `meson test` 注册（meson.build 中无 `test()` 调用）
- 无 `make check` 目标
- 无 pytest/其他测试框架入口

测试策略：依赖 test_package 中的消费者端到端用例验证库功能。

## 依赖分析

gsound meson.build 声明的依赖：

```
gio = dependency('gio-2.0')
gobject = dependency('gobject-2.0')
libcanberra = dependency('libcanberra')
```

对应 conan 依赖：
- glib2/2.88.0（提供 glib-2.0 / gobject-2.0 / gio-2.0 / gmodule-2.0）
- libcanberra/0.30

## 平台适配决策

### 1. 关闭可选功能

| meson 选项 | 默认值 | 适配后 | 原因 |
|-----------|--------|--------|------|
| introspection | true | false | gobject-introspection 不在工具链，交叉编译不可用 |
| gtk_doc | false | false | gi-docgen 不在工具链 |
| enable_vala | true | false | valac 不在工具链 |

### 2. GObject 单副本（gsound 变体方案）

ohpcd 只发布 static glib2。gssdp/gupnp 的方案是置空 GLib 系 .pc 的 Libs，
g_* 符号全 UND，运行时统一解析到 libsoup-3.0.so 的唯一 gobject 副本。

但 gsound **不链接 libsoup3**，没有可借用的 GObject 导出表——直接照搬
gssdp 方案会在链接期报 `g_hash_table_unref`/`g_object_ref`/
`g_direct_hash`/`g_task_new` 等 undefined symbol（第四轮迭代实测）。

gsound 的适配方案：**保留**静态 glib2 链接列表（.pc 只修 `prefix=`，
不动 Libs），libgsound.so 直接链接唯一的 glib 副本；单副本性由
"消费进程不引入第二个 GObject 共享库"保证（conanfile.py glib2-pc-fix
处的 NOTE 注释）。

### 3. 共享库 codesign

OHOS loader 校验 .codesign 段哈希：
- tc.strip = None（禁止 strip）
- meson install 后用 build 目录原始产物覆盖（避免 DT_RUNPATH 清理破坏哈希）

### 4. gnome.mkenums 交叉编译

gsound/meson.build 使用 gnome.mkenums() 生成枚举代码。需将 glib2 包 bin 目录的
glib-mkenums 钉入 meson 原生 [binaries] 段。

## 文件清单

```
archives/g/gsound/
├── README.md
├── manifest.yaml
├── commands.json         # 纯库包，无命令行工具（type: library）
└── 1.0.3/
    ├── conanfile.py
    ├── conandata.yml
    ├── manifest.yaml
    ├── notes.md
    ├── patches/          # 无补丁
    └── test_package/
        ├── CMakeLists.txt
        ├── MANIFEST.yml
        ├── conanfile.py
        └── test_gsound.c
```

## 验证结果

conan create（2026-09-30，ohos-aarch64 profile，conan 2.29.1）通过：

- 编译：libgsound.so.0.0.2 构建成功；test_package 消费者编译/链接/运行全通过
- 消费者用例 6 步：ctx 创建 / open / set_attributes / play_simple 全 PASS；
  cache 在 OHOS 无音频后端下报 Invalid argument（非致命 INFO，环境限制）；
  unref PASS；退出码 0
- conan-verify G0–G4 全 PASS（reports/conan-verify-report.md，Verdict: PASS）
- finish W2/W3 全 PASS：W3 本地 CI L0/L1/L4/L5 pass、L2 纯库 skip
  （reports/w3-local-ci.log，Pass rate 100.0%）；W2 无框架越权改动
- 迭代修复记录：include 路径整理（扁平安装 → package() 归位 include/gsound/）、
  SONAME 实体副本（musl 不跟随符号链接）、静态 glib2 直链（无 libsoup3 导出表）、
  zlib 根级 override 1.3.1.1（PIC）、build 产物覆盖安装 .so（.codesign 哈希）
- 日志：reports/conan-create.log、reports/w3-local-ci.log、
  reports/conan-verify-report.md

---

**编译结束**: 2026-09-30 17:45
**最终状态**: built
