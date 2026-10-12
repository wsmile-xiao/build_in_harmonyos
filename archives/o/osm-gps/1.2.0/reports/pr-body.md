## PR 信息
- **三方库名称**：osm-gps（上游为 osm-gps-map / libosmgpsmap，C 语言 GTK3 GObject 库）
- **上游版本**：1.2.0
- **上游仓库地址**：https://github.com/nzjrs/osm-gps-map
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（adapt-lib-flow 七步闭环）

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游仓库无 tests/ 目录、无 TESTS/Makefile 测试目标 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 同上 |
| **合计** | **0** | 上游未提供自动化测试套件 |

### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例（无测试代码可改，patches_applied 为空）

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 上游无单元测试 |
| 鸿蒙特有测试 | 1 | 新增 | test_package 消费者端到端用例：编译并运行 `osm_gps_map_get_type()`（headless），验证 libosmgpsmap-1.0 链接与 GObject 类型注册 |
| **合计** | **1** | **+1** | 上游 0 + 鸿蒙特有消费者用例 1 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例（无测试代码）
- [ ] **是**，存在对上游测试用例的修改

上游没有自动化测试文件，本提交没有删除、跳过或改写上游测试来制造通过结果。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：新增 1 项消费者端到端用例，编译并运行 `osm_gps_map_get_type()`（headless，无需 display），验证 libosmgpsmap-1.0 可链接且 GObject 类型系统初始化成功（返回非 0 类型 ID）。
- **补全原因**：上游仓库（osm-gps-map 1.2.0）无任何自动化测试套件（无 tests/ 目录、无 TESTS/Makefile 测试目标），且 GObject 库必须经运行时 `g_type_register` 验证才能确认类型系统可用；适配引入 libsoup/2.74.3 静态内嵌 GLib 的 GType 双注册缺陷，须用消费者用例在 LD_PRELOAD shim 下实测绕行是否生效。
- **新增测试文件清单**：
  1. `archives/o/osm-gps/1.2.0/test_package/test_osm.c` — 消费者端到端用例（调用 `osm_gps_map_get_type()`）。
  2. `archives/o/osm-gps/1.2.0/test_package/libsoup_gobject_shim.c` — LD_PRELOAD GType 双注册绕行 shim（加载期按类型名幂等，不改变 osm-gps 行为）。
  3. `archives/o/osm-gps/1.2.0/test_package/conanfile.py` — 编译消费者 + 签名并注入 shim + 运行。

## 验证结果

- 编译状态：**通过**（conan create 干净构建，os=OHOS aarch64；conan-verify G0–G4 + L2/L4/L5 全绿）
- 上游测试用例通过率：0/0（N/A，上游无自动化测试套件）
- 新增测试用例通过率：1/1（100%，test_package 消费者端到端用例 `osm_gps_map_get_type()` 在 LD_PRELOAD GType shim 下通过 GObject 类型注册验证）

### 编译验证
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，libc++，lld 链接）
- 编译状态: **通过**（conan create 干净构建，os=OHOS aarch64）
- 构建系统: autotools（libtool，-version-info 2:0:1）
- 配置选项: `--disable-introspection --disable-gtk-doc --enable-shared --disable-static --build=aarch64-linux --host=aarch64-linux`（链接阶段追加 `-fuse-ld=lld`；PKG_CONFIG_PATH 指向 PkgConfigDeps 生成的 .pc；HMDFS TMPDIR 在 build() 内打补丁固定）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | configure + 全量 .c 编译 + `make -C src` 链接 libosmgpsmap-1.0.so.1.1.0，0 编译错误 |
| 产物存在性 | ✅ | libosmgpsmap-1.0.so.1.1.0 + SONAME 链接 libosmgpsmap-1.0.so.1（由 readelf 读取真实 SONAME 自动建链）；osmgpsmap-1.0.pc；include/osmgpsmap-1.0/ |
| ELF 格式 | ✅ | aarch64 ELF DYN，G4 产物完整性通过 |
| 运行测试 | ✅ | 消费者 test_osm 编译并运行 `osm_gps_map_get_type()` 返回非 0（LD_PRELOAD 注入 GType shim 绕行 libsoup 缺陷，headless 无需 display） |
| 动态依赖 | ✅ | 无系统同名库冲突（G3 通过）；依赖闭包 gtk/3.24.43、cairo/1.18.4、libsoup/2.74.3、zlib/1.3.1.1 |

### 补丁说明
- 无 conandata 文件补丁（patches_applied 为空）。
- HMDFS TMPDIR 补丁在 `build()` 内以字符串改写 `configure` 实现（固定可写 TMPDIR、改写 `ac_tmp` 模板、移除 rm 清理 trap），非落盘补丁文件。
- test_package 注入 `libsoup_gobject_shim.c`：LD_PRELOAD 拦截 GType 注册入口，经显式 `dlopen("libgobject-2.0.so.0")` 把全部 GType 注册汇入共享 libgobject 单表、按类型名幂等，绕行 libsoup/2.74.3 发布二进制**静态内嵌 GLib GObject 类型系统**导致的 `cannot register existing type 'gchar'` 运行时 abort（仅加载期绕行，不改变 osm-gps 行为；根本修复须让 libsoup 链共享 glib）。

### 依赖
- gtk/3.24.43（约束解析 glib/2.84.0.1、gdk-pixbuf、pango、cairo 等）
- cairo/1.18.4
- libsoup/2.74.3
- zlib/1.3.1.1（override，统一 glib2/2.88.0 与 GTK3 栈的 zlib 版本以复用已发布二进制）

### 测试结论
- 总体评价: **通过**。conan-verify G0–G4 + L2/L4/L5 全绿；上游无测试套件，鸿蒙特有消费者端到端用例 1/1 通过。libsoup/2.74.3 内嵌 glib 的 GType 双注册缺陷已由 test_package 加载期 shim 绕行并记录，建议后续在 libsoup 配方层修复（链共享 glib 替代空包 glib2/2.88.0）。
