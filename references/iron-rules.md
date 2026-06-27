> 本文件从 SKILL.md 提取，详细内容供按需加载。

# 铁律与 AI 执行风格规范

来源: SKILL.md §1.2

## 铁律总表（32 条，违反=bug）

| # | 规则 | 正确做法 | 禁止 |
|---|------|---------|------|
| R1 | **参数最少化** | `./configure --prefix=$P && make` | 加 `--build/--host`/CFLAGS hack |
| R2 | **探索阶段不生成 .patch** | 只改源码+记录到 notes.md | diff/sed 结果写文件 |
| R3 | **补丁只用 ohc-run.py refresh-patch** | `ohc-run.py refresh-patch --auto` | 手动 diff/AI 写 patch |
| R4 | **危险库静态编译** | 在 conanfile.py `generate()` 中设置 `--without-shared` / `BUILD_SHARED_LIBS=OFF` | 编译共享库导致系统崩溃 |
| R5 | **软链接必须验证可执行 + 禁止 ln -sf** | `ls -la` 验证 + `rm -f && ln -s` | 只检查 `-L` 存在性 / `ln -sf` 覆盖 |
| R6 | **禁止修改生成文件** | 只改 configure.ac/CMakeLists.txt/*.c/*.h（源码层） | sed 改 configure/Makefile/Makefile.in（不可复现） |
| R7 | **安全弹窗必须先触发再测试** | make install 后 `find bin -type f -exec {} --version \;` | 直接跑 make check 不触发弹窗→进程被杀→假阴性 |
| R8 | **源码修改"四不"准则** | `#ifdef __OHOS__` 守卫 / 保持上游风格 / 追加平台分支 | 删跨平台代码 / 硬编码路径 / 改原逻辑流 / 偏离代码风格 |
| R9 | **质量门禁 FAIL 禁止标 success** | conan_verify 非零 → 降级为 built/failed | 产物有问题仍标记成功 |
| R10 | **临时文件必须用 $TMPDIR** | 所有 tmp 文件操作使用 `$TMPDIR` 或 `$HOME/tmp` | 硬编码 `/tmp`（鸿蒙 /tmp 只读，见 E002） |
| R11 | **脚本步骤失败必须先查归档再动手** | 读 `archives/{pkg}/{ver}/README.md` + `manifest.yaml` 获取历史方案 | 直接手动摸索 / 忽略已有补丁和解决方案 |
| R12 | **遇到错误必须先匹配错误模式再修复** | 搜索 `knowledge/error-patterns.md` + 引擎匹配 graph/index.tsv | 凭直觉试错 / 重复踩已知坑 |
| R13 | **脚本调用必须使用完整路径** | `python3 $SKILL_ROOT/scripts/ohc-run.py <command>` | `./scripts/xxx` 相对路径 |
| R14 | **脚本失败=手动模式入口，非终止** | 失败时按提示切换手动模式，完成后 `--resume-from=StepN` 继续 | 脚本 exit 后 AI 放弃 |
| R15 | **历史仅供参考，不盲从** | 实际参数以本次编译为准，成功后回写 manifest + conanfile.py | 盲目复用历史错误参数 |
| R16 | **协作不越权** | 不推送 main，走 PR 流程 | 直接推送 main 分支 |
| R17 | **知识先草稿** | graph add --draft | 直接写正式图谱 |
| R18 | **依赖先查预编译** | resolve-deps --install 优先于手动编译 | 直接手动编译依赖 |
| R19 | **禁止手动打包，必须用 conan create** | `conan create` 构建 + `conan upload` 发布 | 手动 `tar czf` / 手动 install.sh |
| R20 | **~~DESTDIR 模式~~（已废弃）** | Conan 自带构建隔离 | 手动 DESTDIR staging |
| R21 | **探索阶段结束必须自检零介入** | 按 compile-guide.md 清单逐项检查，所有手动操作已固化为 conanfile.py | 不自检就调 finish |
| R22 | **finish 前必须通过 conan 验证** | `conan_verify` PASS（conan create 从干净源码构建成功） | conan verify 失败仍标 success |
| R23 | **平台检测机制优先于改生成文件** | 用 hints/config.guess/cmake 检查 | 手动 sed config.sh/config.h |
| R24 | **归档清理：failed必删，空归档删** | 无产物无补丁的归档无价值 | 保留无用归档 |
| R25 | **notes.md 防重复：先删后写** | finish 自动清理旧记录，只保留最后一次 | 多次 finish 产生重复记录 |
| **R26** | **终端工具必须静态链接** | conanfile.py `generate()` 中强制 `BUILD_SHARED_LIBS=OFF` / `-static` / `default_library=static` | 动态链接导致 DevBox 部署后找不到 .so |
| **R27** | **依赖引用必须 @ohpcd/stable** | `self.requires("name/ver@ohpcd/stable")` | 裸 `self.requires("name/ver")` |
| **R28** | **conanfile.py 必须有 test_package/** | 生成 conanfile.py 时同时生成 test_package/ | 只有 conanfile.py 没有测试 |
| **R29** | **conan_verify 通过后才标记 published** | `ohc-run.py conan-verify` PASS + CI upload → published；PASS 未 upload → built；FAIL → failed | conan create 失败仍标记 published |
| **R30** | **conan-verify 失败必须查询知识图谱** | G2 失败时调用 `run_engine()` 匹配 E-entry | 只打印错误不查图谱 |
| **R31** | **知识图谱未命中必须生成草稿** | `knowledge/drafts/DRAFT-*.kv` 自动生成 | 未命中的错误丢弃不沉淀 |
| **R32** | **Conan recipe 平台判断兼容 OHOS** | `self.settings.os in ("Linux", "OHOS")` | `self.settings.os == "Linux"` |

---

### R4 详细说明：危险库静态编译（v3.0 更新）

> **v3.0 变更**：R4 从探索阶段的 configure 参数迁移到 conanfile.py 的 `generate()` 方法。

危险库（如 ncurses）编译为共享库会导致鸿蒙系统崩溃。在 conanfile.py 中：

```python
# CMake 项目
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["BUILD_SHARED_LIBS"] = "OFF"  # R26 + R4
    tc.generate()

# Autotools 项目（ncurses 特殊参数）
def generate(self):
    tc = AutotoolsToolchain(self)
    tc.configure_args.append("--without-shared")  # R4 特殊参数
    tc.extra_ldflags.append("-static")             # R26 通用静态
    tc.generate()
```

| 危险库 | 特殊参数 | 原因 |
|--------|---------|------|
| ncurses | `--without-shared` | .so 导致系统崩溃 |
| openssl | `no-asm` | 无汇编支持 |
| bash | `--without-bash-malloc` | 使用系统 malloc |

---

### R19 详细说明：禁止手动打包（v3.0 强化）

> **v3.0 变革**：手动 tar.gz + install.sh 打包完全废弃，由 Conan 体系替代。

```
❌ 禁止: ohc-run.py package → tar.gz → install.sh → curl | sh
✅ 正确: conanfile.py → conan create → conan upload → conan install
```

**原因**：
1. 手动 tar.gz 的 ELF 未签名（鸿蒙上不可执行）
2. 手动打包缺少 RPATH、未 strip 符号
3. install.sh 维护成本高，每个软件一个
4. Conan 体系自带依赖解析、版本管理、产物隔离

**废弃的模块**：
- `package_builder.py` — 9步 tar.gz 打包管线
- `sign_elf.py` — ELF 签名（由 ci/artifacts/sign.sh 替代）
- `packaging/` 目录 — 不再生成

---

### R20 详细说明：~~DESTDIR 模式~~（已废弃）

> **v3.0 废弃**：Conan 自带构建隔离，不再需要手动 DESTDIR staging。

| 旧模式 (v2.x) | 新模式 (v3.0) |
|--------------|--------------|
| `configure --prefix=$DEFAULT_PREFIX` | conanfile.py `settings` + `layout` |
| `make install DESTDIR=$TEST_PREFIX` | `conan create` 自动隔离 |
| `ohc-run.py package` 从 staging 打包 | `conan create` 自动打包 |
| 手动 G1-G4 验证 | `conan_verify` + 五级测试 |

**探索阶段仍可用 DESTDIR**：AI 在探索性编译时可以用 `make install DESTDIR=...` 验证产物，
但最终交付必须是 conanfile.py + `conan create`，不是手动 DESTDIR 产物。

---

### R26 详细说明：终端工具必须静态链接

> **核心原因**：DevBox 部署终端工具时只拷贝 `bin/` 下的可执行文件，没有 `lib/` 目录。

鸿蒙 PC 的额外限制：
- **无 root**：不能往 `/usr/lib` 装系统级动态库
- **RPATH bug**：鸿蒙对 `$ORIGIN/../lib` 相对 RPATH 解析不稳定
- **HMDFS**：分布式文件系统的软链接行为异常

**两类包的不同策略**：

| 包类型 | 举例 | 链接方式 | 部署方式 |
|--------|------|----------|---------|
| **终端工具** | curl, bash, make, bzip2 | 强制静态 | conan install → 拷 bin/ |
| **开发库** | openssl, zlib, libcurl.a | 动态或静态均可 | 留 conan cache 供构建消费 |

**各构建系统配置**：

| 构建系统 | 静态链接配置 | 在 conanfile.py 中的位置 |
|----------|-------------|------------------------|
| CMake | `tc.variables["BUILD_SHARED_LIBS"] = "OFF"` | `generate()` |
| Autotools | `tc.extra_ldflags.append("-static")` + configure `--enable-static --disable-shared` | `generate()` |
| Makefile | 只编译静态目标（不编译 shared） | `build()` |
| Meson | `tc.project_options["default_library"] = "static"` | `generate()` |

---

### R27 详细说明：依赖引用必须 @ohpcd/stable

所有 conanfile.py 中的依赖引用必须使用完整格式：

```python
# ✅ 正确
def requirements(self):
    self.requires("openssl/1.1.1w@ohpcd/stable")
    self.requires("zlib/1.3.1@ohpcd/stable")

# ❌ 错误 — 缺少 user/channel
def requirements(self):
    self.requires("openssl/1.1.1w")
    self.requires("zlib/1.3.1")
```

**原因**：
1. CI 的 `conan create` 使用 `--user=ohpcd --channel=stable` 统一注入
2. 依赖图的自动生成靠解析 `self.requires(...)` 中的 `@ohpcd/stable`
3. CNB Conan 制品仓的包标识格式为 `{name}/{version}@{user}/{channel}`

---

### R28 详细说明：conanfile.py 必须有 test_package/

每个 conanfile.py 必须配套 `test_package/` 目录，作为 Conan L1 官方测试。

**最低要求**：
- `test_package/conanfile.py` — 测试配方
- `test_package/CMakeLists.txt` 或 `test.c` — 验证程序

**CI 行为**：`conan create` 在构建完成后自动执行 `test_package/`，失败则整体失败。

**模板**：参见 `templates/test_package/`

---

### R29 详细说明：conan_verify 通过后才标记 published

```
探索性编译成功 → 生成 conanfile.py → conan_verify
                                    ├─ PASS → status=published
                                    └─ FAIL → status=built (需修复)
```

`conan_verify` 执行：
1. `conan create` 从干净源码构建（验证配方自包含性）
2. `conan test` 执行 test_package（L1 测试）
3. `readelf -d` 检查静态链接（R26）
4. 产物完整性检查（bin/lib/include）

只有 conan_verify PASS 才能标记 `status: published`。

---

### R30 详细说明：conan-verify 失败必须查询知识图谱

> **核心原则**：探索阶段（Step 3-8）已有知识图谱匹配，Conan 阶段（Step 9-10）同样必须查询。

当 `conan create` 在 G2 门禁失败时，`conan_verify.py` 自动调用 `engine.py` 的 `run_engine()`：

```
conan create 失败
  ↓ 提取错误输出
  ↓ run_engine(error_text)
  ├─ 命中 E-entry → 展示根因 + 修复命令 + 详细文档
  └─ 未命中 → 生成草稿（R31）
```

**已有的知识覆盖**：
- E007: config.guess 不识别 HarmonyOS → 自动修复补丁
- E011: mktemp -d 在 HMDFS 上权限异常 → umask 修复
- E092: CMAKE_SYSTEM_NAME 不识别 → cmake toolchain 修复

如果这些知识在 Conan 阶段被查询到，AI 可以直接应用修复而不需要重新探索。

---

### R31 详细说明：知识图谱未命中必须生成草稿

> **核心原则**：每次编译中发现的新问题都不能丢弃，必须沉淀为知识。

当 `run_engine()` 未匹配到任何 E-entry 时，`conan_verify.py` 的 `_create_draft_entry()` 自动：

1. 提取错误关键词（`_extract_keywords()`）
2. 截取错误摘录（前 1000 字符）
3. 生成 `knowledge/drafts/DRAFT-NNN.kv` 文件
4. 文件格式与正式 E-entry 一致，TODO 字段待填写

**草稿提升流程**见 `knowledge/drafts/README.md`。

**与 R17 的区别**：
- R17: 手动新增知识也用草稿（`graph add --draft`）
- R31: conan-verify 自动生成草稿（无需手动触发）

---

### R21 详细说明：探索阶段自包含性检查

探索阶段是试错阶段，AI 可能通过手动操作绕过问题。结束时必须自检：所有手动操作是否已固化为 conanfile.py？

**检查清单**：
1. 所有 configure 参数 → 已写入 conanfile.py `generate()`
2. 所有补丁 → 已在 conandata.yml 中声明
3. 所有依赖 → 已在 conanfile.py `requirements()` 中声明
4. 静态链接 → conanfile.py `generate()` 已设置
5. test_package/ → 已创建且可运行

---

### R22 详细说明：conan 验证（替代旧 G0 干净构建）

`conan create` 本身就是"干净构建"——Conan 从 tarball 下载源码、应用补丁、构建、安装到隔离目录。
不需要单独的 G0 干净构建验证步骤。

`finish` 的 Step 3 改为调用 `conan_verify`：
1. `conan create archives/{l}/{name}/{ver}/ -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. 检查退出码
3. 检查产物完整性
4. 检查静态链接

---

### R8 详细说明：源码修改"四不"准则

> **核心原则：你的修改对非鸿蒙平台必须是透明的。**

| 不 | 含义 | 错误示例 | 正确做法 |
|----|------|---------|---------|
| **不破坏上游逻辑** | 不删除/反转/改变原有代码行为 | 删除某个 `if (linux)` 分支 | 用 `#elif defined(__OHOS__)` 追加新分支 |
| **不破坏跨平台兼容性** | 不删除其他平台的已有适配 | 删掉 `#ifdef _WIN32` 块 | 保留所有平台守卫 |
| **不绕过鸿蒙标识机制** | 不硬编码平台特征 | `if (strstr(path, "/usr/local") != NULL)` | `#ifdef __OHOS__` |
| **不偏离上游代码风格** | 缩进/命名/注释风格与项目一致 | 项目 4 空格你用 tab | 读周边代码保持一致 |

---

### R32 详细说明：Conan recipe 平台判断兼容 OHOS

> **核心原因**：目标平台 `os=OHOS`（见 profile `ohos-aarch64`）。如果 recipe 内部用 `self.settings.os == "Linux"` 做平台判断，OHOS 不命中，导致 Linux-like 行为（fPIC、system_libs 选择等）被错误跳过。

```python
# ❌ 禁止：OHOS 不命中
if self.settings.os == "Linux":
    self.cpp_info.system_libs = ["dl", "rt"]

# ✅ 正确：OHOS 作为 Linux-like 平台同时命中
if self.settings.os in ("Linux", "OHOS"):
    self.cpp_info.system_libs = ["dl", "rt"]
```

注意：绝大多数 recipe 不需要手动判断 `settings.os`——CMakeToolchain / AutotoolsToolchain 会自动处理平台差异。只有 recipe 内部确实需要按平台分支时（如选择 system_libs、条件编译选项等），才适用本规则。

---

## AI 执行风格规范

### 测试脚本原则

| ✅ 推荐 | ❌ 禁止 |
|---------|--------|
| 每个测试一条独立验证 | 单次 tool_call 写 >30 行复杂 shell |
| 变量先赋值再使用 | 管道内嵌套命令替换 |
| 用 `$TMPDIR/$HOME/tmp` 替代 `/tmp`（R10） | 硬编码 `/tmp` |
| `grep -F` 做固定字符串匹配 | grep 不加 `-F` 匹配含元字符的输出 |
| 逐条顺序执行，每步可独立验证 | 一次性提交大量命令 |

### configure/make 长时间命令

```bash
# ✅ 正确：给足够 timeout，不提前中断
cd $BUILD_SRC_DIR && ./configure --prefix=$DEFAULT_PREFIX 2>&1 | tail -3
#   autotools timeout=600s, 其他 timeout=300s
```

### configure 预期耗时参考

| 构建系统 | 典型软件 | 预期耗时 |
|----------|---------|---------|
| autotools | 小工具 | 3-8 min |
| autotools | 大型 | 10-20 min |
| cmake | 一般项目 | 1-3 min |
| meson | 一般项目 | <1 min |

---

## 失败处理标准流程（R11+R12 强制执行）

```
脚本/编译步骤失败
  │
  ├─ [R11] 第一步：查归档记录
  │   ├─ 读 archives/{pkg}/{ver}/README.md
  │   ├─ 读 archives/{pkg}/{ver}/manifest.yaml
  │   └─ 读 archives/{pkg}/README.md（软件级）
  │
  ├─ [R12] 第二步：匹配错误模式
  │   ├─ 引擎匹配: ohc-run.py engine "错误日志"
  │   ├─ 快速查找: grep -i "关键词" knowledge/graph/index.tsv
  │   └─ 搜索同类软件的 conanfile.py / manifest.yaml
  │
  └─ [诊断完成] 第三步：基于历史方案动手修复
      → 归档和知识库都没有 → 记录为新问题
      → 修复后更新 notes.md + conanfile.py + 继续
```
