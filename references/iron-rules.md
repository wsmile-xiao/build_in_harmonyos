> 本文件从 SKILL.md 提取，详细内容供按需加载。

# 铁律与 AI 执行风格规范

来源: SKILL.md §1.3

## 铁律总表（49 条，R1-R49，违反=bug）

| # | 规则 | 正确做法 | 禁止 |
|---|------|---------|------|
| R1 | **参数最少化** | `./configure --prefix=$P && make` | 加 `--build/--host`/CFLAGS hack |
| R2 | **探索阶段不生成 .patch** | 只改源码+记录到 notes.md | diff/sed 结果写文件 |
| R3 | **补丁只用 ohc-run.py refresh-patch** | `ohc-run.py refresh-patch --auto` | 手动 diff/AI 写 patch |
| R4 | **危险库静态编译** | 在 conanfile.py `generate()` 中设置 `--without-shared` / `BUILD_SHARED_LIBS=OFF`（R26 子集） | 编译共享库导致系统崩溃 |
| R5 | **软链接必须验证可执行 + 禁止 ln -sf** | `ls -la` 验证 + `rm -f && ln -s` | 只检查 `-L` 存在性 / `ln -sf` 覆盖 |
| R6 | **禁止修改生成文件** | 只改 configure.ac/CMakeLists.txt/*.c/*.h（源码层） | sed 改 configure/Makefile/Makefile.in（不可复现） |
| R7 | **安全弹窗必须先触发再测试** | make install 后 `find bin -type f -exec {} --version \;` | 直接跑 make check 不触发弹窗→进程被杀→假阴性 |
| R8 | **源码修改"四不"准则** | `#ifdef __OHOS__` 守卫（须有实质逻辑，禁止空壳 stub）/ 保持上游风格 / 追加平台分支 | 删跨平台代码 / 硬编码路径 / 改原逻辑流 / 偏离代码风格 / `#ifdef __OHOS__` 空壳 stub（return 0 绕过功能） |
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
| **R26** | **系统同名库禁止动态链接** | conanfile.py `generate()` 中对系统同名库强制 `BUILD_SHARED_LIBS=OFF` / `-static` | 构建系统同名 .so 污染 `/lib`/`/lib64` 导致其他应用崩溃 |
| **R27** | *(已废弃 — 制品仓已完成无 channel 迁移，依赖引用默认就是 `name/version` 格式)* | — | — |
| **R28** | **conanfile.py 必须有 test_package/** | 生成 conanfile.py 时同时生成 test_package/ | 只有 conanfile.py 没有测试 |
| **R29** | **conan_verify 通过后才标记 published** | `ohc-run.py conan-verify` PASS + CI upload → published；PASS 未 upload → built；FAIL → failed | conan create 失败仍标记 published |
| **R30** | **conan-verify 失败必须查询知识图谱** | G2 失败时调用 `run_engine()` 匹配 E-entry | 只打印错误不查图谱 |
| **R31** | **知识图谱未命中必须生成草稿** | `knowledge/drafts/DRAFT-*.kv` 自动生成 | 未命中的错误丢弃不沉淀 |
| **R32** | **Conan recipe 平台判断兼容 OHOS** | `self.settings.os in ("Linux", "OHOS")` | `self.settings.os == "Linux"` |
| **R33** | **build() 禁止依赖未定义 shell 环境变量** | 从 Conan Toolchain / `self.conf_info` / `AutotoolsToolchain` 获取编译器路径与标志 | 裸用 `${CC}` / `${CFLAGS}` / `${CXX}` 等 shell 变量 |
| **R34** | **test 必须实质依赖被测包** | test_package 源文件调用被测包 API / 执行被测包二进制 | 只打印字符串的空壳 test（即使链接了被测库但不调用任何函数） |
| **R35** | **禁止用 conan list/search 判断 binary 是否存在** | 用 `conan install --requires=...`（dry-run）或 `conan download` 验证预编译包 | 用 `conan list "*/*:*/*" -r=xxx` 判断（cnb.cool 服务端搜索 API 对 binary 返回不完整） |
| **R36** | **依赖必须先发布再构建下游** | 依赖包必须先通过 release 流水线发布到制品仓（`conan upload` 完成），再适配/构建依赖它的下游包 | 在依赖包尚未发布时就构建下游包（`--build=missing` 会尝试从源码编译依赖，耗时且容易失败） |
| **R37** | **版本号 = 上游版本 + 适配修复后缀** | 首次用 `X.Y.Z`，修复适配问题后用 `X.Y.Z.N`（N 从 1 递增） | 同一版本号重复上传不同 revision（制品仓 409 拒绝），或每次修复都改版本号 |
| **R38** | **命令行工具必须声明 commands.json** | 构建产物包含可执行文件的包，必须在**软件级别**目录下创建 `commands.json` | 命令行工具缺少 commands.json，或库类型误加 commands.json |
| **R39** | **源码 URL 必须为官方源** | conandata.yml 中的 URL 必须指向官方正式源（GitHub releases、官方网站）或权威镜像源，CI 自动添加镜像 fallback | 使用个人 fork、网盘、不明 CDN 作为源码下载地址 |
| **R40** | **深度适配库需验证适配完整性** | 图形渲染/UI框架/多媒体/外设/系统底层类库，编译通过不等于适配完成，需检查实质性平台适配代码（非 stub） | 仅编译通过但无平台适配补丁，或 test_package 只调用 version() 无实际功能验证 |
| **R41** | **外部依赖阻塞止损** | registry/git remote 连续 3 次不可达且超 30 分钟 → 立即写 result.json 止损；多包任务单包止损不连坐；剩余预算 <40min 只收尾 | 无限重试外部阻塞；多包任务因单包阻塞全部放弃 |
| **R42** | **PR 创建即上报** | PR 创建成功即写 result.json partial 草稿，工具化监控 CI（红→修复→push→`submit --resume`；绿→自动升级 success）；`--no-wait` / `OHC_SUBMIT_NO_WAIT=1` 可跳过等待 | 自己写 sleep 盲等 CI / AI Review |
| **R43** | **调参螺旋止损** | 同一错误类别连续 5 次调参失败 → 停止调参，写 result.json（failed_build + 5 次尝试证据）退出 | 无证据盲试调参死循环 |
| **R44** | **CI 失败必须先自诊断再修** | CI 红后先 `gitcode_pr.py diagnose` 二次归类再定向修复；本地 W3 复验后才 push | 对"未知"失败盲改重推 |
| **R45** | **SKILL_FEEDBACK 防丢失** | 骨架前置+事件累积+终态兜底+完成入仓四道工具化防线；AI 只填 4 个建议占位符 | 流程结束才手工补反馈（猝死即丢） |
| **R46** | **result.json 全程生命周期草稿** | 五挂点自动写 draft 草稿；终态只走 `result` 命令 | 手写 JSON / 猝死无上报 |
| **R47** | **语言预检前置** | 主流程前跑 `lang-preflight`；非 C/C++ 立即终态 env_unsupported | 非 C/C++ 源码硬走 conan 流程 |
| **R48** | **预算感知收尾** | 长阶段前 `budget-check` 三态：ok / near_limit(立即收尾) / exhausted(断点终态) | sleep 盲等 CI 烧光预算 |
| **R49** | **依赖注入必须用 build_folder 私有 prefix** | 注入目标=`build_folder/prefix`，CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH 全指向私有 prefix | 注入共享 /usr/local（CI/本地互相污染，E524） |

---

### R4 详细说明：危险库静态编译（R26 子集）

> R4 是 R26 的特例：某些库（如 ncurses）一旦构建为共享库会直接导致系统崩溃，这些库同时是系统同名库的极端案例。

危险库（如 ncurses）编译为共享库会导致鸿蒙系统崩溃。这些库同时也是系统同名库（R26），在 conanfile.py 中：

```python
# CMake 项目
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["BUILD_SHARED_LIBS"] = False  # R26: 系统同名库静态
    tc.generate()

# Autotools 项目（ncurses 特殊参数）
def generate(self):
    tc = AutotoolsToolchain(self)
    tc.configure_args.append("--without-shared")  # ncurses 特殊参数
    tc.configure_args.append("--disable-shared")   # R26 通用静态
    tc.generate()
```

| 危险库 | 特殊参数 | 原因 |
|--------|---------|------|
| ncurses | `--without-shared` | .so 与系统同名，加载导致系统崩溃 |
| readline | `--disable-shared` | .so 与系统同名 |
| zlib | `BUILD_SHARED_LIBS=OFF` | .so 与系统同名 |

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

### R26 详细说明：系统同名库禁止动态链接

> **策略变更**：旧版要求所有终端工具一律静态链接，因为早期无 Conan 依赖管理，用户无法自动下载依赖链。
> 现在由 Conan 管理依赖链，**默认改为动态链接**，仅系统同名库保留静态约束。

**核心原因**：构建产出的 `.so` 如果与系统 `/lib`、`/lib64` 下已有 `.so` 同名，
安装后会覆盖系统库，导致其他应用加载错误版本而崩溃。

**链接策略**：

| 类型 | 链接方式 | 说明 |
|------|----------|------|
| 系统同名库 | **必须静态** | `.so` 名与 `/lib`、`/lib64` 冲突 → 静态链接 |
| 其他库 | **默认动态** | Conan 管理依赖链，`conan install` 自动拉取全部传递依赖 |

**系统同名库判断**：
```bash
ls /lib*/**/lib<name>.so* /lib/**/lib<name>.so* 2>/dev/null
# 如果有同名 → 必须静态链接
```

**依赖管理原则**：
- 所有第三方依赖**必须在 `requirements()` 显式声明**
- **禁止**硬编码系统路径（`-L/storage/.../usr/local/lib`）
- 系统库仅限 libc/libm/libdl 等基础运行时

**各构建系统静态配置（仅系统同名库使用）**：

| 构建系统 | 静态链接配置 | 在 conanfile.py 中的位置 |
|----------|-------------|------------------------|
| CMake | `tc.variables["BUILD_SHARED_LIBS"] = False` | `generate()` |
| Autotools | `--disable-shared --enable-static` | `generate()` |
| Makefile | 只编译静态目标（不编译 shared） | `build()` |
| Meson | `tc.project_options["default_library"] = "static"` | `generate()` |

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
                                    └─ FAIL → status=failed
```

`conan_verify` 执行：
1. `conan create` 从干净源码构建（验证配方自包含性）
2. `conan test` 执行 test_package（L1 测试）
3. `readelf -d` 检查系统同名库未输出 .so 到系统路径（R26）
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

> **工具化（v12.17）：** preflight PF5 门禁机械拦截——PR 变更的 patches/*.patch 新增行（+ 开头）含 `__OHOS__` 即 fail-closed，上下文行与历史存量豁免；例外场景需 PR 说明理由后 `--no-preflight` 显式跳过（留痕可审计）。

> **核心原则：你的修改对非鸿蒙平台必须是透明的。**
>
> **注意**：源码中可以使用 `#ifdef __OHOS__` 守卫（允许），但 patches/ 补丁文件中不应引入 `#ifdef __OHOS__`，应通过 POSIX 兼容方式修复（如修改 config.guess/config.sub、条件检查等）。

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

### R33 详细说明：build() 禁止依赖未定义的 shell 环境变量

> **核心原因**：CI/release worker 上 shell 环境变量（`$CC`、`$CFLAGS`、`$CXX` 等）可能未设置。在 `self.run()` 中裸用 `${CC}` 时，shell 展开为空字符串，导致 make 用空值编译——**编译静默失败（Error 127），但 make 继续执行**，最终 package() 打出空包，test() 找不到二进制。

#### 典型反面案例（sponge/0.70 真实事故）

```python
# ❌ 禁止：$CC 和 $CFLAGS 在 release worker 上为空
def build(self):
    apply_conandata_patches(self)
    self.run('make sponge -j1 CC="${CC}" CFLAGS="${CFLAGS} -Wall"')
    # 实际执行: make sponge -j1 CC="" CFLAGS=" -Wall"
    # make 输出: Wall sponge.c -o sponge → Wall: No such file or directory
    # Error 127 (ignored by make) → 无 sponge 二进制 → test() 失败
```

#### 正确做法（按构建系统分类）

**CMake 项目**（不需要手动传编译器，Toolchain 自动处理）：
```python
def build(self):
    apply_conandata_patches(self)
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

**Autotools 项目**（AutotoolsToolchain 自动注入 CC/CFLAGS）：
```python
def generate(self):
    tc = AutotoolsToolchain(self)
    tc.generate()  # 自动写入 CC、CFLAGS、LDFLAGS 到 conanbuildenv

def build(self):
    autotools = AutotoolsToolchain(self)
    autotools.configure()
    autotools.make()
```

**Makefile 项目**（必须显式传入编译器，不能依赖 shell 变量）：
```python
def generate(self):
    env = VirtualBuildEnv(self)
    env.generate()
    # 从 Conan settings 获取编译器路径
    cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)
    cxx = self.conf.get("tools.build:compiler_executables:cpp", "clang++", check_type=str)
    # 写入 env 确保可追溯
    env = Environment()
    env.define("CC", cc)
    env.define("CXX", cxx)
    env.vars(self).save_script("conanbuild")

def build(self):
    apply_conandata_patches(self)
    self.run("make -j1 CC=$CC CXX=$CXX")
    # $CC 此处来自 Conan 生成的 env 脚本，不是 shell 环境变量
```

#### 经验法则

| 场景 | 正确获取方式 | 错误获取方式 |
|------|-------------|-------------|
| 编译器路径 (CC/CXX) | `self.conf.get("tools.build:compiler_executables:c")` | `$CC` / `${CC}` |
| 编译标志 (CFLAGS/CXXFLAGS) | `AutotoolsToolchain` / `CMakeToolchain` 自动注入 | `$CFLAGS` / `${CFLAGS}` |
| 链接器路径 (LDFLAGS) | `requirements()` 声明依赖，Conan 自动处理 | 手动 `-L/path -lfoo` |
| 架构标志 (ARCH) | `self.settings.arch` | `$ARCH` / `${ARCH}` |

> **L0h 门禁**：CI 在 conan create 之前会扫描 conanfile.py，检测 `self.run()` 中的 `${CC}` / `${CFLAGS}` / `${CXX}` / `${LDFLAGS}` 模式，命中则直接拦截。

---

### R34 详细说明：test 必须实质依赖被测包

> **核心原因**：PR #1795 (bird/3.1.6) 的 test_package/test.c 只有一个 `printf("test bird 3.1.6: OK\n")`，不调用 bird 的任何 API，即使 bird 库完全损坏也能通过。这是"形式合规、实质空壳"的假测试——通过了 L0c（有源文件）、L0d（test() 调了 self.run()）、L1d（不是 echo/print/true）所有检查。

#### 典型反面案例

```c
// ❌ bird/test_package/test.c — 假测试
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    printf("test bird 3.1.6: OK\n");  // 不调用 bird 的任何函数
    return 0;
}
```

即使 CMakeLists.txt 写了 `target_link_libraries(test bird)`，链接器发现 test.c 没有引用 bird 的符号，不会从 libbird.a 提取任何 .o，链接照样成功。

#### 正确做法

```c
// ✅ 真测试 — 调用被测包 API
#include <stdio.h>
#include <bird/bird.h>   // 引入被测包头文件

int main(void) {
    bird_ctx *ctx = bird_init();      // 调用被测包函数
    if (!ctx) {
        fprintf(stderr, "FAIL: bird_init() returned NULL\n");
        return 1;
    }
    bird_route *r = bird_lookup(ctx, "192.168.1.0/24");
    printf("test bird: route lookup OK (r=%p)\n", (void*)r);
    bird_free(ctx);
    return 0;
}
```

#### L1e 破坏性反向验证（CI 兜底，无法绕过）

CI 在 conan create 成功后执行 L1e：

1. 从 conan cache 找到被测包产物
2. **mv 移走整个产物子目录**（bin/、lib/、include/）
3. 重新 `conan test`（重新编译 test 源码 + 链接 + 运行）
4. 如果仍然 PASS → 假测试（test 不依赖被测包）
5. 如果 FAIL → 真测试（链接/运行确实依赖被测包）
6. mv 目录回原位，恢复产物

**破坏策略选择 mv 目录而非逐文件篡改的原因**：

- 鸿蒙系统 MAC 策略下，`make install` 安装的文件可能只读，`cp`/`printf` 覆盖会报 `operation not permitted`
- Conan 创建的 package 目录本身当前用户可写，mv 目录只需父目录权限
- mv 整个目录比逐文件 find/cp/rm 更可靠，且无 zsh glob 兼容性问题

**无法绕过的底层保证**：

| 包类型 | 破坏方式 | 真测试的表现 | 底层保证 |
|--------|---------|-------------|---------|
| 静态库 .a | mv lib/ 移走 | 链接器找不到库 → cannot find -lxxx | 链接器必须找到库文件 |
| 动态库 .so | mv lib/ 移走 | 加载器找不到库 → cannot open shared object | NEEDED 记录强制加载 |
| 可执行包 bin | mv bin/ 移走 | test 执行 bin 找不到命令 → command not found | 进程执行不可伪造 |
| 头文件库 | mv include/ 移走 | 编译器找不到声明 → No such file or directory | 预处理器必须解析声明 |

> 提交者无论在 CMakeLists.txt、源码、conanfile.py 哪一层做手脚，都无法改变链接器/加载器/预处理器的确定行为。

---

### R35 详细说明：禁止用 conan list/search 判断 binary 是否存在

> **核心原因**：cnb.cool 的 Conan 服务端对搜索 API（`/v2/conans/search`）的 binary package 查询支持不完整——`conan list "*/*:*/*" -r=xxx` 返回 recipe 信息但显示 "No packages found for this revision"，即使该包的预编译二进制已成功上传且可正常下载。这会导致 AI 和人工误判"制品仓没有预编译包"，进而做出错误的决策（如重新编译、修改 upload 逻辑等）。

#### 三套 API 路径对比

| 操作 | Conan API 路径 | cnb.cool 支持情况 |
|------|---------------|------------------|
| `conan list "*/*:*/*" -r=xxx` | 搜索 API (`/v2/conans/search`) | recipe ✅ binary ❌（返回空） |
| `conan install --requires=...` | 解析 API (`/v2/conans/resolve`) | recipe ✅ binary ✅ |
| `conan download "pkg/ver@user/ch"` | 下载 API (`/v2/conans/download`) | recipe ✅ binary ✅ |

#### 正确做法

```bash
# ✅ 验证某个包是否有预编译 binary — 方法一：dry-run install
conan install --requires="zlib/1.3.1" -pr="ohos-aarch64" --build=missing

# ✅ 验证某个包是否有预编译 binary — 方法二：直接 download
conan download "zlib/1.3.1" -r=ohpcd

# ✅ 查看制品仓有哪些 recipe（仅 recipe 列表，不含 binary 状态）
conan list "*/*" -r=ohpcd

# ❌ 错误 — 用 list 查 binary，会得到 "No packages found" 的误判
conan list "*/*:*/*" -r=ohpcd
```

#### 判断规则

- 需要**判断 binary 是否存在** → 用 `conan install` 或 `conan download`
- 需要**列出制品仓有哪些包**（recipe 层面） → `conan list "*/*" -r=xxx` 可以用，但结果只反映 recipe，不代表 binary 状态
- **绝对禁止**用 `conan list "*/*:*/*"` 的结果判断"制品仓是否有预编译包"

---

### R36 详细说明：依赖必须先发布再构建下游

> **核心原因**：公开制品仓的核心价值是"一次发布、多方复用"。如果依赖包 A 尚未发布到制品仓，下游包 B 声明了 `self.requires("A/x.x")`，CI 构建时 `--build=missing` 会尝试从源码编译 A——这通常因为缺少 A 的构建依赖（工具链/传递依赖）而失败，或者耗时数倍于预期。更严重的是，即使侥幸成功，本地产物与制品仓中的正式版本可能不一致，破坏可复现性。

#### 依赖发布优先级流程

```
适配包 B（依赖 A）
  │
  ├─ Step 1: 检查 A 是否已发布到制品仓
  │   conan install --requires="A/x.x" -r=ohpcd
  │
  │   ├─ 已发布 → 继续 Step 2（正常流程）
  │   │
  │   └─ 未发布 → 必须先适配并发布 A
  │       ├─ 切换到 A 的适配流程
  │       ├─ A 通过 CI + release 流水线发布到制品仓
  │       └─ A 发布成功后，再回来构建 B
  │
  ├─ Step 2: 在 B 的 conanfile.py 中声明依赖
  │   self.requires("A/x.x")
  │
  └─ Step 3: CI 构建 B 时，--build=missing 从制品仓拉取 A 的预编译包
```

#### 反面案例

```python
# ❌ B 的 conanfile.py 依赖了 A，但 A 还没发布
class BConan(ConanFile):
    requires = "A/1.0"  # A 尚未发布到制品仓
    # CI 构建时: --build=missing 试图从源码编译 A
    # 结果: 缺少 A 的构建依赖 → 编译失败 → 误判为 B 的适配问题
```

#### 多层依赖链

当依赖链为 `C → B → A` 时：

1. **先发布 A**（无外部依赖的基础库，如 zlib/openssl）
2. **再发布 B**（声明 `requires("A/...")`，从制品仓拉取 A）
3. **最后发布 C**（声明 `requires("B/...")`，从制品仓拉取 B）

**CI 在构建 C 时，完整的依赖解析链为**：
```
C (本次构建)
  → B (制品仓预编译包)
    → A (制品仓预编译包)
```

只有每一层都先发布，下游才能通过 `--build=missing` 快速拉取预编译依赖，避免全链路从源码编译。

#### 与 R18（依赖先查预编译）的关系

- **R18** 是适配阶段的原则：优先查预编译包，有就用、没有再考虑编译
- **R36** 是发布阶段的优先级原则：**没有发布的依赖，必须先走发布流程**
- 两者结合：适配时先查预编译（R18），如果发现依赖未发布，先发布依赖（R36），再继续适配

---

### R37 详细说明：版本号 = 上游版本 + 适配修复后缀

> **核心原因**：cnb.cool 制品仓不支持同一 `name/version` 下多个 recipe revision 并存（上传新 revision 会返回 409 Conflict）。因此，每次适配修复必须递增版本号后缀来区分。

#### 版本号格式

```
X.Y.Z     ← 首次适配（= 上游版本）
X.Y.Z.1   ← 第 1 次适配修复
X.Y.Z.2   ← 第 2 次适配修复
X.Y.W     ← 上游新版本（后缀重置）
```

#### 什么算"适配修复"

需要递增后缀的场景：
- conanfile.py 构建标志错误（如漏了 `-fPIC`）
- 补丁文件缺失或不正确
- package_info 的 libs 写错
- test_package 修复
- 任何 conanfile.py / conandata.yml 的修正

**不需要**递增后缀的场景：
- 上游发布新版本 → 直接用新版本号
- 代码 review 中的文字修改（注释、README 等）→ 不影响构建产物

#### 正确流程

```bash
# 首次适配
conan create . --name=zlib --version=1.3.1
conan upload "zlib/1.3.1" -r=ohpcd -c

# 发现 CMake 标志错误，修复后重新发布
# 修改 conanfile.py (如添加 -fPIC)
conan create . --name=zlib --version=1.3.1.1
conan upload "zlib/1.3.1.1" -r=ohpcd -c
```

```python
# 下游 conanfile.py
self.requires("zlib/1.3.1")      # 用首次版本（如果不需要修复）

# 如果下游依赖了某个修复版，显式指定
self.requires("zlib/1.3.1.1")    # 需要第 1 次适配修复
```

#### 下游引用更新规则

当 zlib 从 `1.3.1` 升到 `1.3.1.1` 时：
- **不需要**强制所有下游立即更新引用
- 下游 `requires("zlib/1.3.1")` 仍然有效（指向首次版本）
- 如果下游遇到 zlib/1.3.1 中的 bug 且在 1.3.1.1 中修复了，才需要更新引用

#### 制品仓中的共存

```
制品仓:
  zlib/1.3.1        ← 首次适配
  zlib/1.3.1.1      ← 第 1 次修复
  zlib/1.3.1.2      ← 第 2 次修复
```

所有版本独立存在，下载时精确指定：
```bash
conan download "zlib/1.3.1"   -r=ohpcd
conan download "zlib/1.3.1.2" -r=ohpcd
```

#### CI 门禁 (L0j)

PR 构建时，CI 自动执行版本号占用检查：

1. 用 `conan download` 检查制品仓中是否已存在 `pkg_name/pkg_ver`
2. 如果已存在，diff 比较本地 conanfile.py/conandata.yml 与制品仓中的
3. 内容不同 → **fail**，提示递增版本号

```
[fail] L0j: zlib/1.3.1 already published with different recipe (R37)
       制品仓中已存在 zlib/1.3.1, 且本次修改了 conanfile.py 或 conandata.yml
       cnb.cool 制品仓不支持同版本多 revision 并存 (409 Conflict)
[hint] 适配修复必须递增版本号后缀:
         zlib/1.3.1 → zlib/1.3.1.1
```

本地预检也可用 preflight_check.sh 提前发现此问题。

#### 追溯适配历史

```bash
# 制品仓中查看所有版本
conan search "zlib/*" -r=ohpcd

# Git log 查看适配修改历史
git log --oneline -- "archives/z/zlib/"
```

---

### R38 详细说明：命令行工具必须声明 commands.json

> **核心原因**：hicmd 项目通过 commands.json 自动发现和安装命令行工具。如果工具类型包缺少此文件，hicmd 无法感知该包提供的命令行能力，用户无法通过 hicmd 安装。

#### 判断标准

| 类型 | 判断依据 | commands.json |
|------|---------|---------------|
| **tool** | 构建产物包含可执行文件（`bin/` 目录下有二进制） | **必须**创建 |
| **library** | 构建产物只有库文件（`.a`/`.so`）和头文件 | 不需要 |

**自动判断方法**（CI L0k 门禁使用）：
- conanfile.py 中 `package_info()` 设置了 `cpp_info.bindirs`
- conanfile.py 中有 `RUNTIME DESTINATION bin` 或类似的可执行文件安装
- conanfile.py 中 `package_type = "application"`

#### 文件位置

```
archives/{letter}/{name}/commands.json
```

**软件级别**（与 manifest.yaml、README.md 同级），一个软件一个文件，`versions` 字段聚合所有版本。新增版本时往 `versions` 中追加条目即可。

#### 格式

```json
{
  "name": "strace",
  "description": "系统调用追踪工具，用于诊断和调试程序",
  "homepage": "https://strace.io",
  "type": "tool",
  "versions": {
    "6.19": {
      "ref": "strace/6.19",
      "binary": true
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| name | 包名（与 conan 包名一致） |
| description | 中文描述（一句话说明功能） |
| homepage | 上游官网 URL |
| type | 固定 `"tool"` |
| versions.{ver}.ref | Conan 引用（`name/version`） |
| versions.{ver}.binary | 是否已发布二进制到制品仓 |

#### binary 字段更新规则

- `false`：尚未发布到制品仓（适配中）
- `true`：已通过 release 流水线发布

适配完成并 CI upload 成功后，由 AI 或 finish 步骤将 binary 更新为 `true`。

#### 反面案例

```json
// ❌ 库类型误加 commands.json
{
  "name": "zlib",
  "type": "tool",        // 错误! zlib 是库不是工具
  ...
}

// ❌ commands.json 缺少 version 条目
{
  "name": "strace",
  "type": "tool",
  "versions": {}         // 空! 缺少当前版本
}
```

#### CI 门禁 (L0k)

PR 构建时自动检查：
1. 扫描 conanfile.py 判断是否构建可执行文件
2. 如果是工具类型 → 检查 commands.json 是否存在且格式有效
3. 如果是库类型 → 检查不应有 commands.json
4. warn 级别（不阻塞 PR，但会提示）

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

---

### R41 详细说明：外部依赖阻塞止损

> **核心原因**：外部依赖（制品仓 registry / git remote）不可达属于环境外部因素，重试不会改变结果，只会烧掉预算。禁止无限重试，触发条件满足即止损。

#### 触发条件（任一满足即止损）

- registry / git remote **连续 3 次不可达**且总耗时**超 30 分钟**
- 失败明确属于环境外部因素（上游未发布 / 网络故障）

#### 止损动作

- **立即写 result.json 止损**（status 按现象判定），禁止无限重试
- **多包任务单包止损不连坐**：成功包照常上报不白干，失败包单独止损，最终聚合如实写明
- **剩余预算 <40 分钟只收尾**：不启动新的编译/验证大步骤，只完成已有产物的归档与上报

#### 禁止事项

- 为绕过依赖伪造 `.ci-result.json`、dummy 包顶替、跳过 W3、伪造 result.json——一律禁止

> 实战教训：task 3659 因 registry 不可达反复重试未及时止损，预算耗尽。

---

### R42 详细说明：PR 创建即上报（partial 草稿 + CI 闭环到绿）

> **核心原因**：PR 创建成功是可交付的里程碑。agent 此后若 sleep 盲等 CI / AI Review，被节点超时杀死时 result 未写，已建 PR 的工作量会直接丢失。

#### 标准动作（v12.2：draft-then-close-loop）

1. **PR 创建成功那一刻**：立即写 result.json partial 草稿（`--status partial` + PR 链接）——这是防猝死保底，不是终点
2. **默认继续工具化监控 CI**（`submit` 内置 2400s 轮询），**禁止 agent 自己写 sleep 轮询 CI / AI Review**
3. **CI 红了 ≠ 放弃**：失败详情自动提取进 HANDOFF → 按报错修复 → 本地 W3 复验 → `git push`（CI 自动重跑）→ `submit --resume` 继续监控
4. **CI 绿了**：partial 自动升级为 success（终态）

#### 跳过等待的合法通道

- 工具支持 `submit --no-wait` 或环境变量 `OHC_SUBMIT_NO_WAIT=1`：PR 建后立即返回（partial 草稿已落盘），CI 结果交由 follow-up 任务处理（`submit --resume` 从断点续，不重跑 W1-W4）
- 仅当剩余预算 <40min（R41）或显式 `--no-wait` 时，才允许停在 partial 退出

> 实战教训：task 3681 建 PR #4629 后自己写 sleep 盲等 CI，等待中被节点超时杀死，result 未写被判 failed，丢失 90% 工作量。教训不是"不等 CI"，而是"不裸等"：先落草稿，再用工具轮询，红了修到绿。

---

### R43 详细说明：调参螺旋止损

> **核心原因**：与 R41 互补——R41 管外部阻塞，R43 管内部死循环。同一错误类别连续多次调参失败，基本可断定是方法性错误，继续盲试不会收敛。

#### 触发条件

- **同一错误类别**（如 cmake 组件名 `components`/`cmake_file_name`、目标名、include/lib 路径等 conanfile 调参）**连续 5 次修改仍失败**

#### 止损动作

- 停止调参，写 result.json（`--status failed_build`，`--failed-reason` 附 5 次尝试的错误摘要与已排除的方向）退出

#### 触发前自查

- 错误信息与上次是否同类？若同类，第 5 次尝试前就该收手——5 次同方向失败基本可断定方法性错误（查归档或上游 conanfile 参考）

> 实战教训：task 3681 对 `Qt5::3DCore` 的 component/cmake_file_name/includedirs 反复推演调参 3.5 小时无一次阶段性上报，直到预算耗尽。

### R39 详细说明：源码 URL 必须为官方源

- conandata.yml 中 URL 必须指向官方正式源（GitHub releases、官方网站）或权威镜像源
- 禁止个人 fork、网盘、不明 CDN——来源不可信且随时可能失效
- CI 自动添加镜像 fallback（ghfast.top 等），配方无需自己写镜像
- 佐证：预下载与镜像注入均由 CI/W3 统一处理，配方保持官方 URL 是唯一事实源

### R40 详细说明：深度适配库需验证适配完整性

- 适用范围：图形渲染 / UI 框架 / 多媒体 / 外设 / 系统底层类库
- **编译通过 ≠ 适配完成**：必须检查实质性平台适配代码（非 stub / 非 return 0 空壳）
- 检查点：平台分支是否有真实实现、降级路径是否声明、运行时行为是否验证（test_package 实测）
- 反例：`#ifdef __OHOS__ return 0;` 让所有调用"成功"——功能完全丢失但测试全绿

### R44 详细说明：CI 失败必须先自诊断再修

- CI 红后的第一步：`python3 scripts/gitcode_pr.py diagnose --repo ... --number N`
- CI 侧分类约 60% 落"未知"，diagnose 对评论内嵌失败日志做本地二次归类（链接/编译/cmake/依赖/配方/补丁/权限/网络/文件缺失/测试空壳），输出证据行+修复要点
- **禁止对"未知"失败盲改重推**（采样：同一 PR 反复重推同类失败=纯浪费 CI 额度）
- 修复循环：diagnose → 修复 → 本地 W3 复验 → push → `submit --resume`；连续 2 轮同错误仍红 → 停损上报（衔接 R43）

### R45 详细说明：SKILL_FEEDBACK 防丢失协议

- 反馈不再是"流程走完才生成"，四道工具化防线（AI 无需主动执行）：
  1. **骨架前置**：PR 创建瞬间与 R42 result 草稿同步生成 feedback 骨架（幂等）
  2. **事件累积**：HANDOFF/CI 红绿/pr_created 经单一咽喉自动追加进 `.ohc/feedback-state/` 并刷入骨架时间线
  3. **终态兜底**：result 写盘时自动补骨架并落 `feedback_pending` 字段（失败任务同样产出经验，消灭幸存者偏差）
  4. **完成入仓**：`feedback --resume` 闭环（rc=0）自动 commit+push 任务分支随 PR 进 main
- AI 唯一动作：终局填 4 个建议占位符 + 效率/检视小节
- 运行时状态存顶层 `.ohc/feedback-state/`（gitignore，永不入 PR）；报告存 `feedback/SKILL_FEEDBACK_<id>.md`

### R46 详细说明：result.json 全程生命周期草稿

- 五挂点自动写草稿：init-archive(task_started) / conan-init(recipe_generated) / conan-verify 通过(conan_verify_passed) / finish 启动(w3_finish_started) / submit(pr_created)
- 输出位置兜底：`--out` > `OHC_RESULT_OUT` > `$HOME/ohpcd-ai-worker-result.json`
- 草稿 `draft:true` + `milestone`，终态 `draft:false`（ECS 据此区分"中断待续"与"终态上报"）
- 防降级：终态已写入时不被里程碑草稿覆盖
- AI 约束不变：终态必须走 `result` 命令，禁止手写 JSON

### R47 详细说明：语言预检前置

- checkout 后、进入适配主流程**前**必须跑 `lang-preflight`（scripts/ohc/lang_detect.py）
- 三级判定：manifest > 构建系统 > 源码统计（≥70%）
- 边界规则：C/C++ 混编按主体判（不算 mixed）；pybind11 绑定包判 cpp；辅助脚本不算主体；manifest 与统计矛盾判 mixed
- c↔cpp 为兼容族不迁移（conan 流程通吃）；其余语言不匹配 → 立即终态 `env_unsupported` + `detected_language`（枚举值）+ `language_evidence` 三项（各 ≤200 字符）
- 依据：0828 报告 ~20% 任务浪费在非 C/C++ 源码上

### R48 详细说明：预算感知收尾

- 动态预算/硬杀在平台侧；SKILL 唯一配合项 = 预算接近耗尽时主动收尾
- `budget-check` 命令（scripts/ohc/budget.py）每个长阶段前调用，三态：ok / near_limit（剩余<40min：停止新编译新 PR，立即写 checkpoint 收尾）/ exhausted（exit 3，自动写 `budget_exhausted` 终态 + `checkpoint_steps` 断点数组）
- 预算判定源优先级：OHC_TASK_DEADLINE > OHC_TASK_BUDGET_SEC > OHPCD_BUDGET_MINUTES > 240 分钟兜底
- 详见 SKILL.md §1.3 R48 与 §4.2

### R49 详细说明：依赖注入必须用 build_folder 私有 prefix

> **工具化（v12.17）：** preflight PF6 门禁——PR 变更的 conanfile.py 命中 `environ.get("SYS_PREFIX")`/`environ["SYS_PREFIX"]`/引号包裹的 `/usr/local` 字面量即 fail-closed；参考配方的合法形态（`DEFAULT_PREFIX` 环境覆盖 + `~/usr/local` 用户级默认）豁免。

> **来源**：asterisk-srtp 22.10.1（PR #6055）——19 轮 CI 全部 `C compiler cannot create executables`，本地却永远无法复现。知识条目 E524。

#### 根因链

1. `generate()` 向共享目录 `/usr/local`（SYS_PREFIX）注入依赖库
2. CI worker 与本地**共享同一台机器的文件系统**
3. CI 从制品仓下载的依赖 revision 与本地不同（共享库版 vs 静态库版、.pc 布局不同）
4. 注入后污染共享目录 → clang 链接 configure 的 conftest 找到坏库 → 报编译器不可用
5. 本地恰好有历史遗留的正确库 → 本地永远绿、CI 永远红

#### 正确做法

- 依赖注入目标 = `os.path.join(self.build_folder, "prefix")`（私有 prefix，不碰共享目录）
- CPPFLAGS / LDFLAGS / PKG_CONFIG_PATH 全部指向私有 prefix
- work 目录 = build_folder 子目录（conan 构建目录天然可执行，无需探测）

#### 三个禁止

| 禁止 | 原因 |
|---|---|
| 注入共享 `/usr/local`（SYS_PREFIX） | CI 与本地共享文件系统互相污染（本条根因） |
| `os.access(path, os.X_OK)` 探测 work 目录 | HMDFS chmod 被忽略、权限固定 660，X_OK 恒 False → 永远回退到 noexec 路径 |
| 只加 `ac_cv_prog_cc_works=yes` 不补 REQUIRED 依赖 | 跳过编译器检查后 configure 仍逐项报 uuid/jansson/sqlite3 等缺失，不是银弹 |

#### 参考实现

`archives/a/asterisk-srtp/22.10.1/conanfile.py`（`_prefix()` / `_ensure_uuid` / `_ensure_jansson` / `_ensure_sqlite3`）
