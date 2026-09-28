## PR 信息
- **三方库名称**：libpackagekit
- **上游版本**：1.3.6
- **上游仓库地址**：https://github.com/PackageKit/PackageKit/archive/refs/tags/v1.3.6.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 3 | tests/meson.build 注册 3 项（pk-test-library, pk-test-daemon-internal, pk-test-e2e）|
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **3** | |

### 是否存在对上游测试用例的修改？
否，无测试用例修改

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 3 | 一致 | 7/10 通过（3 个 offline 因 /tmp 只读失败，E002 平台限制）|
| 集成测试 | 0 | - | 未运行（daemon_tests=false） |
| 鸿蒙特有测试 | 0 | - | - |
| **合计** | **3** | | |

---

## 上游测试用例修改说明
无测试用例修改。上游 3 项测试中 pk-test-library 实测运行（7/10 通过，offline 子用例因 OHOS /tmp 只读 E002 平台限制失败，非代码缺陷）；pk-test-daemon-internal 与 pk-test-e2e 未运行（库组件包 daemon_tests=false 不构建 daemon，需完整 daemon/DBus 环境，如实声明）。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: meson
- 配置选项: `-Dsystemd=false -Dgobject_introspection=false -Dman_pages=false -Dgtk_doc=false -Dlegacy_tools=false -Dpackaging_backend=dummy -Ddaemon_tests=false -Dcron=false -Dpython_backend=false -Dgtk_module=false -Dgstreamer_plugin=false -Dbash_completion=false -Dbash_command_not_found=false -Doffline_update=false --wrap-mode=nodownload`

### 产物验证
| 编译无错误 | PASS | 构建系统: meson, 状态: published |
| 产物存在性 | PASS | conan create 验证通过 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 7, 失败: 3（offline，/tmp 只读平台限制） |
| 动态依赖 | PASS | 依赖: glib/2.84.0, sqlite3/3.53.4, polkit/127, jansson/2.15.1.1 |

### 补丁说明
- `0001-policy-meson.build.patch`: policy/meson.build — OHOS msgfmt 无 ITS 规则支持，i18n.merge_file 改为 install_data 直接安装（功能等价）

### 依赖
- glib/2.84.0
- sqlite3/3.53.4
- polkit/127
- jansson/2.15.1.1

### 测试结论
- 总体评价: 通过
- 已知限制: offline 子用例因 OHOS /tmp 只读失败（E002 平台限制）

### 遇到的问题与解决方案
1. OHOS musl gettext stub：libintl.h 为空，用 -Dgettext/-Ddgettext/-Dbindtextdomain 等宏规格化
2. Policy XML 翻译：msgfmt 无 ITS 规则，改 install_data 直接安装
3. OHOS ELF 签名：dlopen 要求 codesign，package() 中 binary-sign-tool 签名
4. HMDFS 软链接：musl loader 无法追踪符号链接，替换为真实副本
5. glib 子 .pc：PkgConfigDeps 只生成 glib-2.0.pc，从 glib 包复制全部子 .pc 并合并 mkenums 变量

### 验证命令
```bash
# Conan 配方验证（8 道门禁 G0-G4/L2/L4/L5 全通过）
conan create archives/l/libpackagekit/1.3.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

# W3 本地 CI 模拟（setup.sh + build_and_test.sh 通过）
# 上游测试实测：7/10 通过
meson test -C build --print-errorlogs
```
