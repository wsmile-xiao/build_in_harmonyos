# DRAFT-selfdata-cli-tool-resource-dir-env-override-packaging — 自带数据资源的 CLI 工具：硬编码资源路径补丁 + runenv 导出打包闭环

> 草稿（DRAFT）。与同目录 `DRAFT-selfdata-cli-tool-resource-dir-env-override-packaging.kv` 成对。

## 适用场景（先判别，别套错条）

CLI 工具满足：①**源码把数据资源目录硬编码**为 FHS 绝对路径（典型
`/usr/local/share/<name>/`）；②构建脚本的 `install` 目标同样硬编码 `/usr/local`
（`mkdir/cp/ln -s` 直写系统前缀，Conan 下不可用）；③资源是**包自身**的
（constellation JSON、模板、帮助文本等），不是某个依赖库的数据。

判别命令：

```sh
grep -nE '/usr/(local/)?(share|lib|etc)' src/* include/*.h   # 命中硬编码路径
grep -nE 'ln -s|INSTALL_DIR|/usr/local' makefile             # install 目标硬编码
```

## 修复模式（四步闭环，starfetch 0.0.4 实证 L0–L5 全绿）

1. **最小源码补丁——环境变量覆盖而非改默认值**：静态路径初始化改为
   `getenv("<NAME>_RES_DIR")` 优先、未设置时**保持上游默认值**（归一尾部斜杠）。
   好处：上游 Linux 安装行为零变化；补丁 diff 最小；平台无关（`#ifdef _WIN32`
   分支不动）。登记进 `conandata.yml` patches，`build()` 首行
   `apply_conandata_patches(self)`（G1 门禁要求该调用）。
2. **不用 install 目标**：build() 直接用 profile 编译器编译（R33：从
   `tools.build:compiler_executables` 取，勿用 `${CXX}` 环境变量）；
   `package()` 手动拷 `bin/<name>` + 资源到 `share/<name>/`。
3. **package_info 导出运行环境**：`runenv_info.define_path("<NAME>_RES_DIR",
   share路径)` + `runenv_info.prepend_path("PATH", bin路径)`。消费者与
   test_package 经 `VirtualRunEnv`（conanrun）零配置获得正确路径。
4. **test_package 经 conanrun 消费**：测试脚本用 `shutil.which("<name>")` 找
   二进制、读环境变量找资源，断言覆盖：资源文件在包内、`-h` 帮助文本、列表、
   指定资源渲染、错误路径、颜色码。L1e 破坏产物后 which/资源断言必失败 →
   真实依赖成立。

## 上游无测试套件时的如实记录

`MANIFEST.yml` 写 `upstream_tests: []`、`upstream_case_count: 0`，验证全部落在
test_package 断言（数量在 MANIFEST/notes/PR 三处一致；**别像本例初稿把 19 写成
12**——以测试脚本实际 check() 计数为准）。

## 与既有条目的差异

| 条目 | 对象 | 修复位置 |
|---|---|---|
| DRAFT-magic-db-load-path-fallback | **依赖库**（libmagic）的运行时数据闭包 | 消费者配方 copy 依赖包数据 + runenv 注入 `MAGIC` |
| DRAFT-script-hardcoded-fhs-paths-need-patch-to-selflocate | **无编译脚本包**的硬编码 FHS 路径 | patch 脚本引入 `$0` 自定位 |
| DRAFT-cobs-c-0.4-no-build-system-pure-c-conan-recipe | 无构建系统纯 C 单文件库的 G1 结构要求 | 配方结构（export_sources/apply_conandata_patches） |
| **本条** | **自带数据资源的编译型 CLI**，源码+install 双硬编码 | **自身源码补丁（env 覆盖）+ package 手动布局 + runenv 导出** |

## 证据

starfetch 0.0.4（Haruno19/starfetch，GPL-3.0，C++17 单文件 + vendored nlohmann/json）：

- 补丁 `0001-runtime-resource-dir.patch`：`STARFETCH_RES_DIR` 覆盖
  `/usr/local/share/starfetch/`，9 行改动，未设环境变量时行为与上游一致。
- 真机 shadow CI（2026-09-29）：L0/L1/L1e/L2/L4/L5 全 pass，19/19 断言，
  Build Summary 100%；`starfetch -h/-l/-n orion/-c red` 均经包内资源渲染。

## 禁止

- ❌ 不要把包前缀绝对路径编译进源码（环境漂移，补丁不可复现；同 magic-db 条的禁令）。
- ❌ 不要因 makefile install 不可用就 tool_requires 构建工具——单文件直编即可。
- ❌ 不要在 test_package 里硬编码包缓存绝对路径——which + conanrun 环境变量即可，
  且这样 L1e 才能证明真实依赖。
