# 编译执行指南（Conan 体系）

> 与 SKILL.md 同步更新，供 Step 2 前/按需加载。替代旧版 DESTDIR 模式。

---

## 1. 编译前置条件

### 1.1 Python + Conan 环境

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- python 3.12.9
pip3 config set global.index-url https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple
pip3 config set global.trusted-host pypi.cnb.cool
pip3 install conan   # OHOS 适配版（基线 2.29.1），勿用官方 PyPI
```

### 1.2 Conan Profile

OHOS 编译 profile 位于 `ci/conan/profiles/ohos-aarch64`：`os=OHOS`、`arch=armv8`、`compiler=clang`、`compiler.libcxx=libc++`。本机原生构建（build=host=OHOS/aarch64），非交叉编译。

### 1.3 加载构建上下文

```bash
source .build-context-<name>-<ver> && cd $BUILD_SRC_DIR
```

`.build-context` 由 `ohc-run.py init-build` 自动生成，含源码路径、依赖信息、G0 预扫描结果。

---

## 2. Conan 配方编译流程

### 2.1 两种模式

| 模式 | 适用场景 | 命令 |
|------|---------|------|
| **A: Conan 驱动** | 已有 conanfile.py / 简单软件 | `ohc-run.py build <name> [<ver>]` |
| **B: 探索性编译** | 首次 / 复杂依赖 / 深度调试 | init-build → 手动编译 → conan-init → conan-verify → finish |

### 2.2 模式 B 流程

```bash
# Step 1: init-build（全自动 9 步）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <name> <ver> [--url=URL]

# Step 2: AI 手动编译（唯一需要智能判断的步骤）
source .build-context-<name>-<ver> && cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
make check  # 必须执行

# Step 2.5: 生成 Conan 配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <name> <ver>

# Step 2.6: 验证配方（8 道门禁）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <name> <ver>

# Step 3: 9 步自动收尾（详见 SKILL.md §3 Step 3）
python3 $SKILL_ROOT/scripts/ohc-run.py finish <name> <ver> published|built|failed
```

> Step 2 中 DESTDIR 仅用于探索阶段隔离测试，最终交付物是 conanfile.py，由 `conan create` 统一构建。

### 2.3 conan-init：生成 Conan 配方

生成 `conanfile.py` + `conandata.yml` + `test_package/`。AI 必须检查：
- `requirements()` 依赖引用必须 ``（R27）
- `generate()` 系统同名库 `BUILD_SHARED_LIBS=OFF`（R26，避免污染 `/lib`）
- `package_info()` 的 `cpp_info.libs` 正确声明
- `conandata.yml` 有 SHA256 校验
- `settings.os` 判断用 `in ("Linux", "OHOS")`（R32）

### 2.4 conan-verify：8 道门禁

| 门禁 | 名称 | 说明 |
|------|------|------|
| G0 | 预构建风险评估 | 知识图谱预查询，非阻塞 |
| G1 | 配方完整性 | conanfile.py + conandata.yml + test_package/ 存在且字段完整 |
| G2 | conan create | 从干净源码构建，验证配方自包含性 |
| G3 | 系统同名库隔离 | readelf -d 检查未输出 .so 到系统路径 |
| G4 | 产物完整性 | bin/lib/include 产物检查 |
| L2 | smoke test | `--version` 可执行 |
| L4 | 安全扫描 | NX / PIE / RELRO |
| L5 | 产物基线 | SHA256 基线对比 |

G2 失败自动调用知识图谱引擎（R30），未命中自动生成草稿（R31）。G2 通过 = 可标记 `published`（R29）。

### 2.5 make check（必须执行）

```bash
make -j1 check 2>&1 | tail -20          # Autotools
ctest --output-on-failure 2>&1 | tail -20  # CMake
meson test -C builddir 2>&1 | tail -20     # Meson
```

| 结果 | 处理 |
|------|------|
| 全通过 | 记录到 reports/test-report.md |
| 部分失败（平台限制） | 记录原因（E046/E051/E002），不阻塞 |
| 全部失败 / core dump | 检查安全弹窗(R7) → 修复后重测 |

鸿蒙预期失败项：E046 (chmod)、E051 (未实现 syscall)、E002 (/tmp 只读)、SELinux 域转换。

---

## 3. 补丁应用

### 3.1 探索阶段规则（R3）

探索阶段**禁止生成 .patch 文件**。只做两件事：①修改源码解决问题 ②在 notes.md 记录修改意图。补丁生成唯一入口是 `ohc-run.py refresh-patch --auto`（finish Step 1 自动执行）。

### 3.2 Conan 配方中的补丁

补丁在 `conandata.yml` 声明，`build()` 中 `apply_conandata_patches(self)` 自动应用：

```yaml
# conandata.yml
patches:
  - patch_file: "patches/0001-fix-ohos-compat.patch"
    patch_description: "修复 OHOS 兼容性"
    patch_type: "portability"
```

### 3.3 平台检测优先（R23）

修改配置前，优先使用软件自身平台检测机制：autotools→config.guess/sub 补丁、perl→hints/、cmake→CMAKE_SYSTEM_NAME 检查。手动改 config.h/Makefile 仅限调试，交付时必须固化为补丁或参数。

---

## 4. 常见问题

### 4.1 错误分类与对策

| 阶段 | 常见错误 | 对策 |
|------|---------|------|
| configure | `command not found` | 缺工具 → 安装预编译包或 `ACLOCAL=/bin/true` |
| configure | `cannot run test program` | conftest pipe → `\| cat` 修复 |
| configure | `invalid host: aarch64-...-ohos` | config.guess/sub 补丁（E007） |
| compile | `xxx.h: No such file` | 缺头文件 → 查依赖链 |
| compile | `-Werror` | CFLAGS 加 `-Wno-error` |
| link | `undefined reference to xxx` | 缺库 → 查 NEEDED 依赖 |
| install | `symlink: File exists` | HMDFS 限制 → `rm -f && ln -s` |

### 4.2 鸿蒙特有陷阱

| 陷阱 | 对策 |
|------|------|
| /tmp 只读 (E002) | 用 `$TMPDIR` 或 `$HOME/tmp` |
| HMDFS 软链接 | `rm -f && ln -s`，不能 `ln -sf` 覆盖 |
| 安全弹窗 | make install 后扫一遍 bin/，首次执行二进制触发确认框 |
| chmod 不生效 (E046) | 记录为平台限制，不阻塞 |
| 未实现 syscall (E051) | setreuid/chroot 等，加入 EXCLUDE_LIST |
| ELF 签名 | CI 流水线 sign.sh |
| ncurses .so 崩溃 | conanfile `--without-shared`（R4） |
| RPATH 不稳定 | 系统同名库强制静态（R26） |

### 4.3 预编译包优先（R18）

依赖缺失**必须先查**：①cmd-pkgs README → `curl install.sh | sh` ②Conan 制品仓 → `conan install --requires=name/ver` ③两者都没有 → 手动编译。

### 4.4 失败恢复

```
失败发生
├─ [R11] 查归档：README.md → manifest.yaml → conanfile.py
├─ [R12] 匹配错误：ohc-run.py engine "错误日志" → E*.kv → 方案
├─ 缺依赖？→ conan install 或 resolve-deps --install
└─ 动手修复：归档+知识库都没有 → 修复 → 记录新问题
```

### 4.5 鸿蒙 sandbox 兼容参数

configure/make 阶段常需：`SED=$(find_tool sed)`、`HELP2MAN=/bin/true`、`MAKEINFO=/bin/true`。详见 `ohc-run.py build` 内置 `find_tool()` 动态检测逻辑。
)` 动态检测逻辑。
