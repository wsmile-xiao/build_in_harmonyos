# 知识候选台账 — libcec 8.1.7（第一轮适配，路径 B 候选评估）

> 本台账按知识治理要求记录：每项非噪声候选的真实错误、根因、修复、验证、
> 适用范围、四范围查重结果与七轴查重结论，最后给出路径决定。
> 适配库：libcec 8.1.7（上游 Pulse-Eight/libcec，tag libcec-8.1.7，CMake/C++）。

## 一、候选清单

### C1. lang-preflight 把含绑定子目录的 C++ 库误判为 rust
- **真实错误**：`lang-preflight` 输出 `detected_language: rust`（exit 2，自动写 env_unsupported 终态），
  但 libcec 主体是 C++（根 CMakeLists.txt，52 个 .cpp / 1 个 .c）。
- **根因**：`lang_detect._manifest_scan` 对**全树文件集合**（`names = {p.name for p in files}`，rglob 递归）
  做 `Cargo.toml` 命中判断，未限定在源码根目录；libcec 8.x 新增 `src/rust/` Rust **绑定**子目录
  （Cargo.toml 在该子目录），子目录 manifest 触发 rust 判定。按 R47 边界规则"绑定类包（pybind11
  等）→ 按主体语言判定"，应判 cpp。
- **修复（判定方法）**：以根构建系统（CMakeLists.txt → cmake/C++）与源码统计（cpp 53/88）为主，
  绑定子目录（rust/dotnet/nodejs）不计入主体语言 → 判 cpp，不采纳误判的 env_unsupported 终态，
  继续 C++ 适配流程。
- **验证**：libcec 8.1.7 按 cpp 完成构建/conan-verify/W3 全通过；R47 的 c↔cpp 兼容族规则下流程畅通。
- **适用范围**：主语言为 C/C++、但源码树含 Rust/.NET/Node/Python 绑定子目录的三方库
  （8.x libcec、pybind11 系、含 src/nodejs 的库等），跨库可复用。
- **四范围查重**：
  - graph/index.tsv：无 lang-preflight/语言预检/绑定误判条目；E105/E154/E172/E180 均为 Rust **工具链**
    缺失类（装 cargo/rustc），与本候选（主体语言判定）触发点不同。
  - knowledge/doc/：无语言判定误判条目。
  - graph/*.kv：同上。
  - knowledge/drafts/：无相同条目。
- **七轴查重**：exact_duplicate=false；causal_duplicate=false；trigger_overlap=部分（与 E105/E154
  同在 rust 域，但触发器是"子树 Cargo.toml 命中 manifest 扫描"而非 Rust 工具链缺失）；
  solution_overlap=无（E105/E154 方案是安装 Rust 工具链，本候选是判定主体语言继续 C++ 流程）；
  combination_novelty=true；boundary_novelty=true；test_migration_novelty=true。
- **结论**：未命中且存在新增差异，**建草稿**（路径 B 候选）。

### C2. OHOS 无 whoami → 上游 SetBuildInfo.cmake 的 string(STRIP) 空值报错
- **真实错误**：CMake configure 失败：`CMake Error at src/libcec/cmake/SetBuildInfo.cmake:39
  (string): string sub-command STRIP requires two arguments.`
- **根因**：libcec 上游在非 Windows 分支用 `find_program(whoami)` + `execute_process(whoami
  OUTPUT_VARIABLE BUILD_USER)` 注入构建信息；OHOS 无 `whoami`（`command -v whoami` → 127），
  BUILD_USER 未定义 → `string(STRIP ${BUILD_USER} BUILD_USER)` 展开为空 → STRIP 缺参崩溃。
- **修复**：`-DDISABLE_BUILDINFO=ON`（上游官方"可复现/嵌入式构建"选项，跳过整个构建信息块），
  优于 patch 改 SetBuildInfo.cmake（零补丁、官方支持）。
- **验证**：不加该选项 configure 必失败；加后手动构建 + conan create + W3 全通过
  （`.ci-result.json` exit_code=0）。
- **适用范围**：所有在 configure 阶段调用 whoami/hostname/git 注入构建信息的 CMake 项目
  （SetBuildInfo.cmake 模式及其同类），OHOS 平台跨库通用。
- **四范围查重**：
  - graph/index.tsv：无 whoami/DISABLE_BUILDINFO/构建信息条目；E117 是 configure_file 模板
    （PACKAGE_STRING 未定义），触发面不同。
  - knowledge/doc/：无。
  - graph/*.kv：无。
  - knowledge/drafts/：无。
- **七轴查重**：exact_duplicate=false；causal_duplicate=false；trigger_overlap=部分（与 E117 同在
  CMake configure 阶段模板注入域，但触发器是缺外部命令而非缺模板宏）；solution_overlap=无；
  combination_novelty=true；boundary_novelty=true；test_migration_novelty=true。
- **结论**：未命中且存在新增差异，**建草稿**（路径 B 候选）。

### C3. CMAKE_SYSTEM_NAME=Linux 使 CMake 生成版本化 SONAME，运行期可加载 libcec.so.8
- **真实错误**：staging 中 `cec-client --version` 报
  `Error loading shared library libcec.so.8: No such file or directory`；
  检查发现构建产物只有裸 `libcec.so`，无 `libcec.so.8` 软链且 ELF 无 SONAME。
- **根因**：OHOS 对 CMake 是未知平台（configure 提示 `System is unknown to cmake`），CMake 未按
  Linux 约定生成版本化共享库命名（SOVERSION 8 → `libcec.so.8` 软链 + SONAME 头）；
  cec-client/cecc-client 的 cecloader 运行期按 `libcec.so.8` 动态加载 → 失败。
- **修复**：conanfile `generate()` 中 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`
  （项目 json-c 同款做法）→ CMake 按 Linux 平台约定生成 `libcec.so.8`/SONAME；
  与 E274（package() 里手动 `os.symlink`）互补，本方案在**构建期**自动生成。
- **验证**：staging 中 cec-client 成功加载并打印 `CEC Parser created - libCEC version 8.1.7`；
  conan-verify G2 通过。
- **适用范围**：OHOS 上所有需要版本化 .so（SONAME）供运行时按 `lib*.so.N` 加载的 CMake 库，
  跨库通用（同 json-c 做法，但 E092 只覆盖"configure 失败"，未覆盖 SONAME 生成这一副作用）。
- **四范围查重**：
  - graph/index.tsv：E092（cmake-toolchain，CMAKE_SYSTEM_NAME 平台检测）、E274
    （create-soname-symlink，package() 手动软链）最接近。
  - knowledge/doc/：E092.md 覆盖"CMAKE_SYSTEM_NAME=Linux 解决 configure"；E274.md 覆盖
    "package() 手动 symlink"方案。
  - graph/*.kv：同上。
  - knowledge/drafts/：无"构建期平台映射自动生成版本化 SONAME"条目。
- **七轴查重**：exact_duplicate=false；causal_duplicate=false；trigger_overlap=部分（E092 同为
  CMAKE_SYSTEM_NAME 平台检测触发）；solution_overlap=部分（cache_variables 写法与 E092 同款，
  SONAME 生成角度与 E274 的手动 symlink 不同）；combination_novelty=true（"平台映射 → 构建期
  自动版本化 SONAME + 运行期 CLI 加载验证"组合无既有条目）；boundary_novelty=true；
  test_migration_novelty=true。
- **结论**：部分覆盖（E092/E274）但存在新增差异（构建期自动 SONAME + 运行期验证），**建草稿**
  （路径 B 候选）。

### C4. make -j jobserver 在 HMDFS 上 mkfifo 失败
- **真实错误**：`make: jobserver mkfifo: .../GMfifo57216: Operation not permitted`。
- **根因**：OHOS SELinux/HMDFS 限制用户进程创建 FIFO；GNU make jobserver 依赖 FIFO。
- **修复**：串行 `make -j1`。
- **验证**：`make -C build`（无 -j）构建成功。
- **查重**：index.tsv **命中 E074**（env-var-override，`make -j1`），doc/E074.md 已完整覆盖。
- **结论**：**完整复用 E074，不建草稿**。

### C5. conan-verify E017 镜像注入残留 conandata.yml.ghfast-bak/.orig
- **真实错误**：conan-verify/CI 对 GitHub URL 临时注入 ghfast.top 镜像，崩溃/中断后残留
  `conandata.yml.ghfast-bak` / `conandata.yml.orig`；JC1 junk_check 拦截、PF7 拒收镜像域。
- **根因**：E017 预防机制备份/恢复的中间态。
- **修复**：提交前清理残留并恢复官方 URL（`conandata.yml` 仅保留官方 github.com URL）。
- **验证**：清理后无残留（`find archives/l/libcec -name "*.ghfast-bak" -o -name "*.orig"` 为空）。
- **查重**：drafts/ 已有 DRAFT-E323（conan-verify-ghfast-bak-rollback）覆盖同问题。
- **结论**：**完整复用既有草稿 DRAFT-E323，不新建**。

## 二、C1-C3 七轴查重明细

| 轴 | C1（绑定子目录语言误判） | C2（whoami/STRIP） | C3（平台映射→SONAME） |
|----|------|------|------|
| exact_duplicate | false | false | false |
| causal_duplicate | false | false | false |
| trigger_overlap | 部分（rust 域，E105/E154） | 部分（cmake configure 域，E117） | 部分（CMAKE_SYSTEM_NAME 域，E092/E274） |
| solution_overlap | 无 | 无 | 部分（cache_variables 同 E092；SONAME 自动生成异于 E274） |
| combination_novelty | true | true | true |
| boundary_novelty | true | true | true |
| test_migration_novelty | true | true | true |

- **覆盖/新增差异**：既有条目覆盖 Rust 工具链缺失（E105/E154）、CMake 平台检测（E092）、
  SONAME 手动软链（E274）、configure 模板缺失（E117）；本库新增：①绑定子目录触发语言误判的
  判定方法；②OHOS 缺 whoami 导致构建信息注入 STRIP 崩溃及 DISABLE_BUILDINFO 方案；
  ③CMAKE_SYSTEM_NAME=Linux 在构建期自动生成版本化 SONAME 的运行期验证。
- **关系字段**：C1 similar_to=E105,E154；C2 similar_to=E117；C3 similar_to=E092,E274；
  caused_by=无；prerequisite_of=无；conflicts_with=无。
- **适用边界/反例**：C1 仅适用于"绑定子目录"场景，纯 Rust 项目（根 Cargo.toml）仍应判 rust；
  C2 仅适用于构建信息注入依赖外部命令的 CMake 项目，DISABLE_BUILDINFO 关闭的是信息注入而非构建；
  C3 仅对共享库版本化命名有效，纯静态库无 SONAME 需求。

## 三、路径决定

- **reuse_existing**：C4（jobserver → E074）、C5（ghfast-bak → DRAFT-E323）。
- **new_draft**：C1、C2、C3 均满足"已验证（真实命令/退出码/日志）、可跨库复用、查重未命中或
  部分覆盖且存在新增差异" → **路径 B（知识库扩展）成立**，建立同 stem 草稿对（.kv/.md）：
  - `knowledge/drafts/DRAFT-libcec-8.1.7-langpreflight-binding-subdir-misdetect.kv/.md`（C1）
  - `knowledge/drafts/DRAFT-libcec-8.1.7-ohos-no-whoami-buildinfo.kv/.md`（C2）
  - `knowledge/drafts/DRAFT-libcec-8.1.7-cmake-system-name-linux-soname.kv/.md`（C3）
- **path_a_no_knowledge**：不适用（本库存在新增知识）。

## 四、查重执行记录（命令与范围）

- 范围 1 graph/index.tsv：
  `grep -inE 'whoami|buildinfo|STRING|STRIP|lang.?preflight|绑定|cargo|rust|jobserver|mkfifo|CMAKE_SYSTEM_NAME|SONAME' knowledge/graph/index.tsv`
- 范围 2 knowledge/doc/：`grep -rliE 'whoami|lang.?preflight|mkfifo|jobserver|CMAKE_SYSTEM_NAME' knowledge/doc/`
- 范围 3 knowledge/graph/*.kv：`grep -riE 'whoami|DISABLE_BUILDINFO|langpreflight|SONAME|jobserver' knowledge/graph/*.kv`
- 范围 4 knowledge/drafts/：`grep -rliE 'whoami|lang.?preflight|mkfifo|jobserver|绑定|语言判定' knowledge/drafts/`
