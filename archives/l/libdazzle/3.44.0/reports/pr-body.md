## PR 信息

- **三方库名称**：libdazzle（GNOME GTK3 辅助控件库）
- **上游版本**：3.44.0
- **上游仓库地址**：https://gitlab.gnome.org/GNOME/libdazzle
- **适配路径**：路径 A（基础适配）
- **使用知识库**：adapt-lib-flow 技能 + ohc workflow（lang-preflight → conan-verify → finish → W4 审计）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 29 | 来源：上游 meson test 套件（`tests/meson.build`，29 个测试可执行文件逐项注册） |
| 集成测试 | 0 | 上游无独立集成测试套件，tests/ 下均为单元/功能性质 |
| 其他测试 | 0 | - |
| **合计** | **29** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 28 可执行通过 | -1 | test-directory-reaper 需创建 symlink，HMDFS 不支持 symlink，平台固有不可执行（根因见 reports/test-report.md），其余 28 项经 broadwayd 无头显示真实执行通过 |
| 鸿蒙特有测试 | 1 | 新增 | test_package 消费者端到端测试（test_libdazzle：GType 注册 / DzlPatternSpec 模式匹配语义 / Levenshtein / 引用计数，16 断言） |
| **合计** | **29** | **-1 / +1** | 上游 28 项通过（1 项平台固有不可执行）+ 消费者 16/16 断言 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

> 上游套件原样经配方侧 `build()` 执行：broadwayd 起无头显示（GDK_BACKEND=broadway），逐测试二进制自签后运行。仅有的测试注册问题来自上游自身 bug（`tests/meson.build` 中 `test('test-signal-group', test_binding_group)` 重复注册同一二进制），未对上游测试源码做任何修改。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有 29 项测试用例覆盖

> test_package 消费者测试为 conan 制品仓标准要求（验证打包产物可链接可运行），非补全上游测试缺口：
> - **新增测试文件**：`test_package/test.c` — 消费者端到端用例，16 断言（依赖注入 → 链接 → 运行 → 断言 API 行为），实测 16/16 通过

## 验证结果

### 编译验证
- 编译器：clang/clang++（aarch64-unknown-linux-ohos，toolchain 注入）
- 编译状态：**通过**（conan create 干净构建，os=OHOS aarch64，conan-verify 全闸门 G0/G1/G2/G3/G4/L2/L4/L5 PASS）
- 构建系统：meson 1.11.0（tool_requires）
- 配置选项：`-Dwith_introspection=false -Dwith_vapi=false -Denable_gtk_doc=false -Denable_tools=false -Denable_tests=true -Dwrap_mode=nodownload -Ddefault_library=shared`

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | libdazzle-1.0 单库构建，0 错误 |
| 产物存在性 | ✅ | libdazzle-1.0.so.0 / libdazzle-1.0.so 别名（HMDFS 无 symlink，实体复制补齐） |
| 头文件与 pkg-config | ✅ | include/libdazzle-1.0/ + libdazzle-1.0.pc（G2 通过） |
| ELF 格式 | ✅ | aarch64 ELF DYN，G4 产物完整性通过，binary-sign-tool 自签 |
| 运行测试 | ✅ | 上游 28/29（broadwayd 无头显示真实执行）+ 消费者 16/16 断言 |
| 动态依赖 | ✅ | glib/2.84.0.1 + gtk/3.24.43 均已发布制品仓且版本与 gtk 配方 pin 对齐（G2/G3 通过） |

### 上游测试通过率

- 上游测试用例通过率：**28/29**（96.6%）
- 新增（消费者）测试用例通过率：**16/16**（100%，N=16 断言实测）

## 可复现命令

```bash
conan create archives/l/libdazzle/3.44.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 -s build_type=Release --user=ohpcd --channel=stable
```

## 补充说明

- 平台适配要点（详见 notes.md）：
  1. el2 HMDFS 对 conan 解压依赖 .so 存在稳定 ENOENT/截断（libdazzle 实证 libpixman-1.so 曾为 16 字节残片）——配方在 `generate()` 将依赖库实体化复制到构建目录镜像并改写 .pc 指向镜像，规避解压产物直接链接；
  2. musl 无 gettext：glib-2.0.pc 的 Libs 追加 `-lintl`（照 gtk/3.24.43 先例）；
  3. glib python 工具（glib-mkenums 等）用编译型 C 启动器 + binary-sign-tool 自签（HMDFS 新脚本 execve 信任抖动）；
  4. 打包 .so 别名（.so.0/.so）因 HMDFS 无 symlink 改为实体复制补齐。
- conandata.yml 使用官方单值 URL（download.gnome.org），sha256 为上游官方 tar.xz 真实哈希；CI 会自动添加镜像 fallback。
- 已知限制：test-directory-reaper 在本平台不可执行（见 reports/test-report.md 根因分析）；submit 自检的 packaging_present 项为框架侧已知误报（对 built 状态库包恒要求 tar.gz，与 PR 禁止预编译产物规则冲突），W4 独立审计（reports/audit-result.json）P0=0 P1=0 通过。
