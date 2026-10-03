# 处理策略：单体仓插件式子项目的适配范式

> 配套文档：`README.md`（识别条件与实测数据）　检测：`detect-cmake-plugin-subproject.sh`　复现：`reproduce.sh`
> 样例：`archives/i/indi-aok/2.0-20221222093242`（1 补丁：仅改构建脚本的组件列表，用于补齐运行期闭包）

## 0. 排查顺序（决策树）

```
配置阶段 find_package(X ...) 失败？
├─ X 是「模块名」（tree 内 FindX.cmake / 仓库级 cmake_modules）→ S1 注入探测提示
├─ X 既无 FindX.cmake 也无 XConfig.cmake（依赖包不提供）→ S2 生成私有 config 包
└─ 两处都齐了仍失败 → 看依赖包代次与请求的组件是否匹配（缺组件库 → 依赖缺口，如实上报）

配置通过但编译失败？
├─ 依赖头文件用到的语言特性/API 高于子项目设定（C++14 vs std::any）→ S3 代次对齐（首选）/ S4 改构建脚本
└─ 头文件路径拼接错（如依赖包 include 下再套一层目录）→ 用 cpp_info 的 includedirs，勿手写相对层级

编译通过但运行失败？
└─ 插件式可执行文件的运行期闭包（dlopen 由主程序发起）→ S5 运行期校验范式
```

## S1 注入探测提示（首选，零源码改动）

**事实**：仓库级 `cmake_modules/FindINDI.cmake` 通过 `INDI_ROOT` 定位 `indiversion.h` 与组件库；
它不读 conan 生成的 `<pkg>-config.cmake`（模块模式与 config 模式互不回落）。

**做法**（配方 `generate()`，路径一律来自依赖对象）：

```python
tc = CMakeToolchain(self)
tc.variables["INDI_ROOT"] = self.dependencies["libindi"].package_folder
tc.generate()
```

**验证**：配置日志出现 `Found INDI: <pkg>/lib/libindidriver.so;<pkg>/lib/libindilx200.so (found version "2.2.2")`。

**禁止**：
- 不要用 `-DINDI_ROOT=/usr/local` 之类的**共享前缀**（R49 / PF6：污染 CI 与本地共享文件系统）；
- 不要为了“顺带修好别的包”往 `CMAKE_PREFIX_PATH` 盲目追加目录（会影响本轮所有 `find_package`）；
- 不要改手写模块里的搜索路径（那是 S4，代价更高）。

**若组件缺失**（`COMPONENTS driver lx200` 找不到 `libindilx200.so`）：这是**依赖制品缺口**，不是配方问题
→ 先补依赖包（R36），勿在本包内自建组件。

## S2 构建目录内生成私有 config 包（信号 2 的标准解法）

**事实**：`find_package(Nova REQUIRED)` 在树内无 `FindNova.cmake` 时转入 config 模式，只认
`Nova_DIR` / `CMAKE_PREFIX_PATH` 下的 `NovaConfig.cmake`；libnova 的 conan 包不提供该文件。

**做法**：在 **generators 目录**（属构建目录，绝不落源码树）写一个最小 config 包，并把 `Nova_DIR` 指过去：

```python
nova = self.dependencies["libnova"]
nova_inc = os.path.join(nova.package_folder, nova.cpp_info.includedirs[0])
nova_libdir = os.path.join(nova.package_folder, nova.cpp_info.libdirs[0])
# libnova 是静态库：给 .a 的绝对路径，避免误取共享库或系统同名库
nova_dir = os.path.join(self.generators_folder, "nova")
save(self, os.path.join(nova_dir, "NovaConfig.cmake"), "\n".join([
    "set(NOVA_FOUND TRUE)", "set(Nova_FOUND TRUE)",
    'set(NOVA_INCLUDE_DIR "%s")' % nova_inc,
    'set(NOVA_INCLUDE_DIRS "%s")' % nova_inc,
    'set(NOVA_LIBRARIES "%s")' % nova_lib,
]))
tc.variables["Nova_DIR"] = nova_dir
```

**要点**：
- 变量名必须与子项目 CMakeLists 使用的**完全一致且大小写相同**（样例用的是 `${NOVA_INCLUDE_DIR}`、
  `${NOVA_LIBRARIES}`，而 `find_package` 的名字是 `Nova`）——先 `grep` 出它到底用哪个变量再写；
- 同时设置 `<Name>_FOUND`/`<NAME>_FOUND` 便于上游 `if(NOVA_FOUND)` 分支；
- 库文件优先按 `cpp_info.libs` 拼名，拼不到再回退扫 `libdir`（不同打包习惯 `libnova.a` / `nova.a` 都见过）；
- 不写 `include_directories()` 到共享前缀；所有路径都来自该依赖的 `cpp_info`（R49）。

**验证**：配置日志不再出现 `Could not find NovaConfig.cmake`；且构建日志/`CMakeFiles/*/link.txt` 中
出现的是依赖包内的 `libnova.a` 绝对路径。

## S3 源码代次对齐（信号 3 首选）

**判据**：制品仓只有**一个**可用代次时，取上游与其次代匹配的 ref（tag 或 commit），而不是旧代次 + 打补丁。

**样例取舍**（写入 `../manifest.yaml` 注释与 `../notes.md`）：

| 选项 | 结论 |
|---|---|
| 用 2.0 代驱动源码 + libindi 2.2.2.1 | ✗ 需改被编译源码（R8 禁止）：属性 API 变更 + `CMAKE_CXX_STANDARD 14` 不够 |
| 用 2.0 代源码 + 改仓库级 `CMakeCommon.cmake` | △ 可行但跨代维护（S4），且仍解决不了被删 API |
| **用 v2.2.2 代源码（同代，上游已自带 C++17/`cmake_minimum_required 3.16`）** | ✔ 0 补丁；驱动自身版本仍为 `Version 2.0`，与任务版本号一致 |

**证据要求**：①`manifest.yaml.source.url` 的注释写清为什么用该 ref；②`notes.md` 记录被否决的替代方案
与实测差异（样例：属性 API 引用处 10 处 vs 7 处、`std::any` 报错行）；③`test_package` 做消费者级校验
（代次对齐可能改变行为，必须真跑一次）。

## S4 改仓库级构建脚本（次选，仅当无法对齐代次）

**约束**：R8（只改构建脚本，绝不改被编译源码）；补丁落点限 `cmake_modules/*.cmake`、`configure` 之类
构建脚本；补丁中**不得引入平台宏**（`__OHOS__` 等，PF5 拦截）。

**样例历史**：pinned 2.0 代的 `FindINDI.cmake` 正则要求 `INDI_VERSION` 为裸数字，而 libindi 包内
`indiversion.h` 是 `INDI_VERSION "2.2.2"`（带引号）→ 曾需打正则补丁；v2.2.2 代上游已自行修好，
这正是「代次对齐优先于打补丁」的成本证据（上游维护 vs 本地长期背补丁）。

## S5 插件式可执行文件的运行期校验范式（编译通过 ≠ 可运行）

**事实**：驱动是**被主程序按需 dlopen 的可执行文件**（`share/indi/*.xml` 登记可执行名）。样例中
`libindilx200.so` 未声明 `NEEDED libindidriver`，符号由后者提供 → 运行期闭包不完整时加载即失败。
更隐蔽的一类是**链接期能过、DT_NEEDED 不全**：样例 `CMakeLists.txt` 只请求 `driver`/`lx200` 两个组件，
`libindiclient` 未入 NEEDED，符号只在链接期经同级 `.so` 间接解析，宿主加载期才报 `symbol not found`。

**test_package 范式**（样例 `../test_package/check_driver.py`，4 项断言）：

| 断言 | 内容 | 失败含义 |
|---|---|---|
| 产物形态 | `bin/<driver>` 存在、非空、`ELF` 魔数、`e_machine=AArch64`、64 位 | 包装缺陷 |
| 数据交叉引用 | `share/indi/<name>.xml` 存在、含驱动名与可执行名，且该可执行名真的在 `bin/` 里 | 包装缺陷 |
| **闭包静态审计（确定性闸门）** | 纯 python 解析 DT_NEEDED：INDI 核心库（`libindiclient`/`libindidriver`/`libindilx200`）齐备、均为裸 soname（无绝对路径）、且都能在依赖包目录内找到 | 打包/链接缺陷 |
| 宿主加载器探针（兜底） | `env="conanrun"` 下真跑一次：宿主拒绝加载（本机 FUSE 下 musl 无法 `mmap(PROT_EXEC)` OHOS 共享库、未签名 ELF）→ **SKIP** 并打印加载器原文；15s 超时仍存活 → **PASS**；缺产物/缺 soname 已被前两条断言拦下 | 区分「平台限制」与「包装缺陷」 |

**要点**：
- 闭包完整性的**判据放在静态审计上**（不依赖宿主能否真加载），加载器探针只作兜底且不得把平台限制
  记成 FAIL——否则本地与 CI 会在同一平台限制上反复红（样例实测：同一批 `.so` 在 conan 缓存目录
  与 `$TMPDIR` 副本上均被拒，属宿主挂载限制，上游 libindi 配方亦用静态链接规避）；
- `conanrun` 环境用于给探针提供完整依赖闭包（而非手工拼 `LD_LIBRARY_PATH`），否则会把依赖库自身的
  传递依赖缺失误判成本包缺陷；
- **必须**保留「删掉 `bin/<driver>` 即 FAIL」的反向特性，满足 CI L1e 破坏性验证；
- 不要把「超时」当作失败——INDI 驱动是长驻进程，超时后仍存活恰恰说明加载成功。

**本条对应策略**：样例采用 S1+S2+S3，并对运行期闭包补了一处 S4 的**构建脚本**补丁
（`find_package(INDI COMPONENTS driver client lx200 REQUIRED)`，补丁内无平台宏，PF5 合规）。

## 兜底

四条策略均不适用（依赖缺组件、上游无同代源码、构建脚本不可改）时：**如实上报 `env_unsupported`
/ `dependency_missing` 并附证据**（实际编译错误行 + `conan download`/`conan list` 探测输出），
不要用 dummy 包顶替或跳过验证。
