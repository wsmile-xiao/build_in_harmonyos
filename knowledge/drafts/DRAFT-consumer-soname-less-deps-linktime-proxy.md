# DRAFT: 消费已发布 soname-less 共享库 —— 链接期 find_package 宏钩子 + patchelf 代理副本

> 配套 `.kv`：`DRAFT-consumer-soname-less-deps-linktime-proxy.kv`
> 状态：Builder path-update 草稿（最终编号 Exxx 由知识库主编确认）
> 申报域：链接（八分类）｜机理分层：L1（链接器/CMake 导入目标语义，平台复发面由制品仓状态保证）｜配额：本 run 1/2（主条）

## 场景

消费已发布的 KF6/Qt 二进制包构建应用：配置、编译、链接全绿，CI 在收尾 ELF
门禁或真机运行时拦下：

```
[fail] L5b: libKF6ConfigWidgets.so 的 DT_NEEDED 含绝对/相对路径:
       /storage/Users/currentUser/.conan2/p/kcode9da5b50c2debb/p/lib/libKF6Codecs.so
```

运行期形态（musl loader，绝对 NEEDED / 坏 NEEDED 链路）：

```
Error relocating .../bin/kgraphviewer: _ZN13KConfigDialog20updateWidgetsDefaultEv: symbol not found
... kgraphviewer --version smoke: rc=127 (FAILED)
```

快查（任何被消费的发布库，命中 SONAME=0 即候选场景）：

```sh
readelf -d "$(ls /storage/Users/currentUser/.conan2/p/kcore*/p/lib/libKF6CoreAddons.so | head -1)" | grep -c SONAME
# → 0
```

实测面：某消费 run 消费面 12/12 导入目标 SONAME=0（KF6::CoreAddons/I18n/
ConfigCore/ConfigGui/ColorScheme/GuiAddons/WidgetsAddons/Service/ItemViews/
WindowSystem/Codecs + Qt6::Core5Compat）。**任何消费这些包的新 run 都会复现**。

## 根因（因果机理链）

1. **发布包缺 SONAME**：制品仓部分 KF6/Qt 包的 `.so` 无 `DT_SONAME`。
2. **链接器语义**：ld 对无 SONAME 的链接输入**原样记录传入路径**。
3. **CMake 导入目标语义**：`IMPORTED_LOCATION(_RELEASE)` 是构建机 conan 缓存
   的机器本地**绝对路径**。
4. **烙印**：产物 DT_NEEDED 记下绝对路径 → 换机器/换缓存布局后路径不存在；
   **绝对 NEEDED 无法用 LD_LIBRARY_PATH/RPATH 补救** → musl loader 按路径解析
   失败，或 CI ELF 门禁拦截。
5. **运行期改写不可行**：patchelf 改写过的文件被 HMDFS 代码签名校验拒绝
   （Permission denied / mmap PROT_EXEC；P-SIGN-001、E537 先例）→ 修复必须
   在**链接期**完成。

## 方案空间（三条常规路全部否定，附定向实验证据）

在 CMake 4.1.2 + OHOS SDK clang/lld 下，对 soname-less 导入目标逐一实验：

| 方案 | 结果 | 证据 |
|---|---|---|
| stamp `IMPORTED_SONAME` / 清 `IMPORTED_NO_SONAME(_RELEASE)` | 不改变链接行 | 设备实验（tmp/soname-exp） |
| `IMPORTED_LOCATION(_RELEASE)` 改写为裸文件名 | clang 驱动当文件路径：`clang-15: error: no such file or directory: 'libKF6WidgetsAddons.so'` | CI r17 |
| `IMPORTED_LOCATION` 改写为 `-l<name>` | make 当 target 依赖：`No rule to make target '-lKF6ConfigCore'` | CI r17 |

### rec：find_package 宏钩子 + patchelf 代理副本（链接期根治）

消费侧 `generate()` 写出 cmake 路径文件（实例名 `conan_cmakedeps_paths.cmake`），
被每个消费工程 include（主构建 + 全部 vendored staging 工程 + test_package，
共 5 处工程验证）。核心三段：

```cmake
set(OHOS_SONAME_LESS_DEPS
    KF6::CoreAddons KF6::I18n KF6::ConfigCore KF6::ConfigGui
    KF6::ColorScheme KF6::GuiAddons KF6::WidgetsAddons KF6::Service
    KF6::ItemViews KF6::WindowSystem KF6::Codecs Qt6::Core5Compat)
set(OHOS_SONAME_PROXIES "${CMAKE_BINARY_DIR}/ohos-soname-proxies")
macro(find_package)
  _find_package(${ARGV})
  ohos_relocatable_link_fixup()
endmacro()
# ohos_relocatable_link_fixup(): 对清单内每个已创建 target，
#   读原 IMPORTED_LOCATION(_RELEASE)（isfile 守卫）→
#   在 proxies 目录生成 patchelf --set-soname <basename> 代理副本
#   （find_program HINTS /data/service/hnp/bin）→
#   set_property(TARGET <t> PROPERTY IMPORTED_LOCATION <代理>)
#   （OHOS_SONAME_PROXY 属性防重复）
```

要点：

- ld 读代理副本的 SONAME → DT_NEEDED 只记**裸名**；运行期
  `LD_LIBRARY_PATH`（**全依赖链** libdir，含传递依赖）按裸名解析到真实发布库。
- 代理副本**仅作链接输入，永不发布**（见 forbid_1）。
- 清单以 `readelf` 逐一实测维护，**不臆测**：新依赖遗漏会被 CI ELF 门禁点名
  （实例：`KF6::Codecs` 即门禁拦下后补录，readelf SONAME=0 确认）。

### fallback：运行期保签名 symlink（诚实权衡）

无法触达链接期时（消费不可改的预编译包），按
`DRAFT-E5xx-registry-so-baked-absolute-needed-symlink` 在烙印绝对路径处建
symlink 指向依赖图内同名真实库（文件内容不变、签名有效），并内联注入全依赖链
LD_LIBRARY_PATH。**权衡**：治标不治本——依赖 HOME 树可写、机器本地、掩盖发布
包缺陷，仅作退路。备选"改 static staging 消费"在本平台有符号可见性边界
（QObject metaobject 单副本语义依赖符号统一），不作为通用退路（经验仓素材）。

## 连锁陷阱：`-L` 内嵌引号经 conan 发射路径断裂（forbid_3）

显式链接闭包（`-L` + `-Wl,-rpath-link` 写入 `CMAKE_{EXE,SHARED,MODULE}_LINKER_FLAGS`）
若路径带内嵌双引号（`-L"/path"`），则：

1. 值经 Conan **CMakeToolchain 发射路径**（`tc.variables[...] = value`）写入
   未转义的 `set(CMAKE_EXE_LINKER_FLAGS "-L"/path" ...")`（工具实现证据）；
2. CMake 按列表解析 set() → CMakeCache 值断裂成 `-L;/path" ...`（`-L` 与路径
   分离 + 尾引号）；
3. 链接行出现 `-L;` 断裂 token → **全部 -L/-rpath-link 目录沉默失效**（构建
   仍 rc=0，非致命）；
4. 直到引入依赖搜索路径的裸名/-l 输入才连锁暴露（clang 驱动错、make
   No rule to make target），误导排障方向。

**复现必须走 conan 发射路径**；手写 toolchain 的转义
`set(CMAKE_EXE_LINKER_FLAGS "-L\"...\"")` **不复现**（缓存值保持完整单 token，
无 `-L;` 断裂）——已设备双分支实测。

自包含复现探针（设备新 shell 可跑，完整 transcript 见本 run
`reports/builder/probes/quote-breakage-probe.log`）：

```sh
mkdir -p /tmp/quote-probe && cd /tmp/quote-probe
cat > conanfile.py <<'EOF'
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, cmake_layout
class P(ConanFile):
    name = "quoteprobe"
    version = "1.0"
    settings = "os", "compiler", "build_type", "arch"
    def layout(self):
        cmake_layout(self)
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = '-L"/tmp/x" -Wl,-rpath-link,"/tmp/x"'
        tc.generate()
EOF
printf 'int main(void){return 0;}\n' > main.c
printf 'cmake_minimum_required(VERSION 3.15)\nproject(quoteprobe C)\nadd_executable(quoteprobe main.c)\n' > CMakeLists.txt
conan install . -s build_type=Release -pr:h=<ci profile> -pr:b=<ci profile>
grep CMAKE_EXE_LINKER_FLAGS build/Release/generators/conan_toolchain.cmake
# → set(CMAKE_EXE_LINKER_FLAGS "-L"/tmp/x" -Wl,-rpath-link,"/tmp/x"" ...)（未转义）
cmake -S . -B b -DCMAKE_TOOLCHAIN_FILE="$PWD/build/Release/generators/conan_toolchain.cmake" -DCMAKE_BUILD_TYPE=Release
grep 'CMAKE_EXE_LINKER_FLAGS:STRING' b/CMakeCache.txt
# → -L;/tmp/x" -Wl,-rpath-link,"/tmp/x""（断裂）
grep -c -- '-L;' b/CMakeFiles/quoteprobe.dir/link.txt   # → ≥1；cmake --build 仍 rc=0
```

历史构建制品佐证（断裂形态与探针同型）：
`/storage/Users/currentUser/.conan2/p/b/kgrap1fb8ae522942c/b/build/Release/` 下
`generators/conan_toolchain.cmake:213`（未转义 `set(... "-L"...`）、
`CMakeCache.txt:110`（`-L;` 断裂 + 尾引号）、
`src/CMakeFiles/kgraphviewer.dir/link.txt`（链接行 `-L;` token）。
**注意**：`-L` 路径写法本身要去引号（平台 conan 缓存路径无空格），
且闭包生效需在 link.txt 抽查确认。

## 与近邻条目的边界

| 条目 | 面 | 与本条差异 |
|---|---|---|
| E537（kpackage !6997） | 打包侧链接自家 soname-less 依赖 | 自己 CMakeLists 可改；其 stamp/裸 -l 手法在本 CMake 4.1.2 + clang 下被否定实验排除，方案换宏钩子+代理 |
| E316 | conan 包内 SONAME symlink 实体缺失 | 包内自修复，非消费侧链接期 |
| E383 | 无 Platform/HarmonyOS.cmake 致产物自身缺 SONAME | 用 `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` 解决，与本条互补 |
| DRAFT-E5xx-registry-so-baked-absolute-needed-symlink | 消费已发布坏包 | 解法在**运行期**（烙印路径 symlink 保签名）；本条在**链接期**（代理副本裸名链接），互补不重叠 |
| E487 | `conan_cmakedeps_paths.cmake` | 仅作 Qt 组件 prefix path 载体，无宏钩子/SONAME 语义 |

## 知识沉淀价值

- **可复用问题类别**："消费已发布的 soname-less 二进制包"——平台制品仓普遍
  状态，复发面由平台保证；诊断（readelf SONAME=0 快查 + NEEDED 烙印路径模式）
  与修复（钩子文件可搬运，5 处工程验证）均与具体库无关。
- **非一次性补丁**：机理（链接器记录语义 + CMake 导入目标 + musl 解析语义）
  与方案空间否定实验均不依赖库细节。
- **附带增量**：`-L` 引号 bug 是独立可复用陷阱——显式链接闭包必须配对有效
  -L，且复现必须走 conan 发射路径（沉默失效，非致命）。

## verification_cmd 摘要

见 `.kv` `verification_cmd` 字段（① SONAME 快查 → ② 引号断裂 conan 发射路径
复现 + 手写负对照 → ③ 修复后裸名 + rc=0）。任何人在 OHOS PC 设备新 shell 可跑。
