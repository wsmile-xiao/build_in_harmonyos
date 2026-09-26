# DRAFT-E720-sexpp-cli-parent-version-gap-attribution — 「父包在档但目标版本缺席」的 CLI 子包：requires 判据与交付面归属

> Contributor: 执行体（session-de4f7e68） | Status: **DRAFT** | Updated: 2026-09-24 | Severity: 2
> Source: `feat/sexpp-cli-0.9.2` 适配 HarmonyOS PC（任务卡 10517）
> 对应：`knowledge/drafts/DRAFT-E720-sexpp-cli-parent-version-gap-attribution.kv`

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-10251-libnfc-tools-1.8.0-tools-subpackage-identification` | 草稿 | `<父>-tools` 拆分包判类；两条路线表：**依赖主包型**（主包该版本在档→requires）/ **自含型**（主库至今未适配→自含）；并明文「主库已有适配只是版本停滞 → 优先按 R36 先适配并发布主库」 | 本条钉的是**中间档**：父包**已有适配（0.8.7/0.9.1 在档）但任务目标版本（0.9.2）缺席**、且任务交付物本身就是 CLI 子包时 → **不 requires、按目标版本源码整编**，libnfc 的「先升父包」条款只在**任务交付物=父包**时才生效（任务面判据，不是配方技术判据）。判据主轴从「依赖可用性」换成「制品归属」 |
| `DRAFT-E618-libheif-libde265-1.23.0-in-tree-plugin-module-subpackage` | 草稿 | 父 tarball 内**插件模块**子包：自含交付宿主（运行期耦合：插件不能脱离宿主）+ N 红线 | 同为「自含交付」但**驱动因不同**：E618 是运行期 dlopen 耦合，本条是**制品仓版本缺席**（CLI 静态内嵌库即可自含，无耦合）；N 红线（父全量注册面 82 ≫ ctest 70）本条同款复用并实证 |
| `DRAFT-fast-cdr-2.3.5-upstream-test-enablement`、`DRAFT-sexpp-0.8.7-gtest-capture-stdout-tmpdir-only` | 草稿 | GTest_DIR 接线面 / 捕获流 TMPDIR 面 | 本条**不重复建条**，只在 notes 引用（本任务同链实测：探针 rc=0、70/70 捕获流复活） |

## 问题

任务卡下发 `sexpp-cli 0.9.2`（新包）。第一动作 `conan list "sexpp/*" -r=ohpcd`
读到：**0.8.7、0.9.1 在档，0.9.2 缺席**。此时有两个反方向的坑：

1. 照「依赖主包型」先例写 `requires("sexpp/0.9.2")` → conan create 依赖解析段
   `dependency_missing` 终止；还会被 W0 生死关第 2 条误判成「缺硬依赖」而止损
   ——但硬依赖根本不缺：**库源码与 CLI 目标就在同一 tarball**，错在 requires
   这个动作本身。
2. 反向过度反应：看到「父包已有适配、版本不齐」就先去升级父包（R36）→
   一 PR 动两个包目录撞 PF1 单包闸，且把交付物从 CLI 换成了父包升级。

## 判据：制品归属，不是依赖可得性

| 读数 | 命令 / 出处 |
|---|---|
| 父包版本分布 | `conan list "sexpp/*" -r=ohpcd` → 0.8.7、0.9.1 在档；**0.9.2 缺席** |
| 库与 CLI 同 tarball | `w0/sexpp-0.9.2/CMakeLists.txt`：`add_library(sexpp …)` + `add_executable(sexpp-cli …)`（RUNTIME_OUTPUT_NAME `sexpp`） |
| 归属先例 | 库制品归 `archives/s/sexpp/`（0.8.7、0.9.1）；本包名即交付物契约 = CLI |

**三选一（按序判）**：

1. 父包**目标版本在档** → `requires` 之，`package()` 只拷工具产物（libnfc 依赖主包型）；
2. 目标版本缺席 **且任务交付物=子包** → **不 requires**：目标版本 tarball 源码整编、
   `BUILD_SHARED_LIBS=OFF` 静态内嵌、`package()` 只交 `bin/<tool>`、
   `package_info()` 清空 includedirs/libdirs/libs、**归属判据写入 notes.md**；
3. 任务交付物=父包本身 → 才走 R36 先升父包（libnfc「版本停滞先升父包」条款**只在此档生效**）。

两条都不取的第三种错误：降级 `requires("sexpp/0.9.1")` —— 交付 0.9.2 声明却链
0.9.1 库面，版本错配假交付（同 E618 forbid_3）。

## 修法（sexpp-cli 0.9.2 实测落点）

```python
# conanfile.py：零 requires（仅 test_requires gtest/1.17.0 跑上游测试）
package_type = "application"
def generate(self):   # BUILD_SHARED_LIBS=OFF 静态内嵌 libsexpp
def package(self):    # 反静默：先断言再拷，只交 CLI
    cli = os.path.join(self.build_folder, "bin", "sexpp")
    if not os.path.isfile(cli):
        raise ConanException(f"sexpp CLI binary not found: {cli}")
    copy(self, "sexpp", src=os.path.join(self.build_folder, "bin"),
         dst=os.path.join(self.package_folder, "bin"), keep_path=False)
def package_info(self):   # 只留 bindirs，清空 include/lib —— 包内零库制品
```

要点：

- **不用 `cmake.install()`**：上游 install 规则带出 lib/include/pkgconfig/man
  （父包面制品），与「只交 CLI」直接冲突；
- **package() 反静默**：`copy()` 对不存在的源是静默零产物，目标路径一变（输出
  目录/改名）就产空包、rc=0，直到 G4/消费侧才爆 —— 必须先 `isfile` 断言；
- **N 红线**（E618 同款，本条实证）：源码宏清点 82（含上游 `add_executable`
  遗漏的 `traits-tests.cpp` 12 个）≫ 未补丁 ctest 70；最小补丁恢复全量枚举后
  82/82。按 70 口径申报即被判少报。

## 验证 / 复现命令（设备可直跑）

```sh
# ① 版本缺席读数
conan list "sexpp/*" -r=ohpcd
# ② 同 tarball：库与 CLI 目标同仓
grep -n "add_executable\|add_library" "$HOME/tmp/sexpp-cli-0.9.2/w0/sexpp-0.9.2/CMakeLists.txt"
# ③ 归属落地：配方零 requires（只 test_requires gtest）
grep -n "requires(" "$HOME/ws/worktrees/sexpp-cli-0.9.2/archives/s/sexpp-cli/0.9.2/conanfile.py"
# ④ 交付面自证（采信轮 G4 后）：包内只有 bin/、无 lib/include
```

## 关键词

父包在档、目标版本缺席、版本不齐、不 requires 父包、源码整编、静态内嵌、
package() 只交 CLI、归属判据、制品归属、Missing prebuilt package、
dependency_missing、R36、PF1 单包闸、sexpp-cli、sexpp/0.9.2、
`<父>-cli`、`<父>-tools`、lensfun-tools、libnfc-tools、同源双包
