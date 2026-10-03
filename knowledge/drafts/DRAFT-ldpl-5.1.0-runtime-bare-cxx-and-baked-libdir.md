# 工具包运行期 fork 裸名外部程序 + 读随包资源：两处常量写死时 env 与 PATH 都救不了，`conan create` 全绿仍是假绿

- 触发库：`ldpl/5.1.0`（`archives/l/ldpl/5.1.0`），HarmonyOS PC（HongMeng Kernel 1.12.0 / aarch64 / toybox），SDK clang 15.0.4
- 阶段：**runtime**（不是 configure/compile/link）
- 严重度：3（不打补丁则该包的核心能力在 OHOS 上 100% 不可用）

## 1. 错误特征（真机原始日志，可直接粘贴复现）

```
* using C++ switch -pthread
* Building hello-bin
sh: c++: inaccessible or not found
LDPL Error: compilation failed.
```

资源目录被烧成别机路径时的第二形态（失败点在被 fork 的编译器里，`ldpl` 自己毫无异常）：

```
#include "/storage/.../.conan2/p/ldpl76837d448d443/p/lib/ldpl/ldpl_lib.cpp"
         ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1 error generated.
LDPL Error: compilation failed.
```

## 2. 触发条件

同时满足两点就会中：

1. 包的**功能**是「生成一段代码/脚本，再交给外部程序执行」——源码里出现
   `system("...")` / `popen("...")` 且命令串以**裸名**开头（`c++`、`g++`、`python`、
   `node`、`perl`、`make`、某解释器）。
2. 该外部程序名在本平台 PATH 上**不存在**。OpenHarmony PC 实测：

```
$ command -v c++ ; command -v g++ ; command -v cc
(全部无输出，RC=1)
$ command -v clang clang++
/storage/Users/currentUser/.harmonybrew/bin/clang
/storage/Users/currentUser/.harmonybrew/bin/clang++
```

上游文档自己把这条写成硬性前置条件（LDPL `docs/index.md`）：
*"you must have a C++ compiler already installed on your system and have mapped it to `c++`, found on your PATH"*。
OHOS 没有这个映射，而且**不该伪造**（R33：编译器必须来自 profile 的
`tools.build:compiler_executables`，PATH shim 绕过审计并遮蔽消费机自己的编译器）。

第二条触发点是同一枚硬币的反面：如果按 conan 习惯把 `self.package_folder` 填进
形如 `-D<某>LOCATION` 的资源定位宏，路径就被烧进二进制。制品仓上传后消费机的缓存路径不同，
运行期才炸，而 `readelf`/`nm` 上完全看不出来 —— L0/L1/L4/L5 门禁没有一条能抓它。

## 3. 根因与实测矩阵

5.1.0 的 `src/ldpl.cpp` 里 `getenv` 出现 **0 次**（`grep -c getenv src/ldpl.cpp` = 0），
所以任何环境变量对上游二进制都是惰性的：给 `CXX`、给 `LDPL_CXX`、给
`LDPL_LIB_LOCATION`，行为一字不变。缺陷是两层的，必须分别对照：

`real` = 资源目录确实存在；`ghost` = 同名空目录（模拟包被搬到别处/路径失效）。
A=未打补丁，B=打补丁（同一份补丁，只改两处常量的取值方式）。

| 组 | 二进制 | 烧死的资源目录 | LDPL_LIB_LOCATION | LDPL_CXX | rc | 结果 |
|---|---|---|---|---|---|---|
| A1 | 未打补丁 | ghost | — | — | 1 | `sh: c++: inaccessible or not found` |
| A2 | 未打补丁 | ghost | real | — | 1 | 同上（LIB env 被忽略） |
| A3 | 未打补丁 | real | — | — | 1 | 同上（**目录指对也没用**） |
| A4 | 未打补丁 | real | — | 给了 | 1 | 同上（**CXX env 被忽略**，决定性） |
| B1 | 打补丁 | ghost | real | 给了 | 0 | 正确输出 `Hello LDPL on HarmonyOS` |
| B2 | 打补丁 | ghost | — | — | 1 | 退回默认值 → 裸名 `c++` 失败 |
| B3 | 打补丁 | real | ghost | 给了 | 1 | `#include "<ghost>/ldpl_lib.cpp"` not found（证明 env 真的生效） |
| B4 | 打补丁 | real | real | 给了 | 0 | 成功 |
| B5 | 打补丁 | real | real(仅 LIB) | — | 1 | 仍失败：两层各自都是必要条件 |

结论：两处常量必须**同时**改成运行期可解析，缺一个都不可用；且失败都发生在
`conan create` 之后的用户第一次调用里。

## 4. 解决方案（推荐 / 禁止）

推荐：一个 portability 补丁，把两处从「编译期常量」降级为「默认值」——

```
LDPL_LIB_LOCATION 优先，否则用编译期 LDPLLIBLOCATION
LDPL_CXX 优先，否则用字面量 "c++"
```

配方侧 `package_info()` 注入 `self.runenv_info.define_path("LDPL_LIB_LOCATION", <pkg>/lib/ldpl)`，
于是**包可重定位**；前端名由消费者/测试从 profile 显式给出。补丁 53 行、
不含任何平台条件编译宏（R8）、非 OHOS 平台默认行为与上游完全一致。

禁止（附实测后果）：

1. **造一个 `c++` 软链塞进 PATH**：本包绿了，但同 runenv 内其它 C++ 包的编译器
   被 clang 冒充的 `c++` 遮蔽；违反 R33，且 CI 与本机不一致。
2. **只把 `self.package_folder` 填进宏就收工**：见 A/B 表，消费即坏，元数据无痕。
3. **test_package 只跑 `-v`/`-h`**：`ldpl` fork 失败时照样正常打印自己的横幅，
   只测 argv 解析等于没测这条包的核心能力。

## 5. 通用性证据（独立语料，非本 PR 自写用例）

语料取自 **LDPL-5.1.0 归档里上游自己写的文档示例程序**（`docs/*.md` 代码块，
与本版本坐标一致），不是我写的 test_package：

- 代码生成差分：50 个样例，39 个可转译；把这 39 个分别在「走烧死路径」与
  「走 `LDPL_LIB_LOCATION`」两种配置下 `ldpl -r` 输出做 md5 对比 →
  **39/39 逐字节相同，差异 0 行**。即补丁不改变生成的 C++，只改变资源来源。
- 行为差分：取其中 6 个样例做真实 `-O0` 编译 + 运行，A/B 两配置输出的 md5
  **每对都相同**（3 个非空、1 个触到 4 KB 截断上限也相同、2 个空输出）；
  同一 6 个样例喂给未打补丁的二进制 → **6/6 `build=1`，签名一律
  `inaccessible or not found`**。
- 反面语料：上游 master 的 `tests/`（21 个程序）在 5.1.0 上 0 个可转译
  （语言已演进，`IMPORT`/module/structure 语法当时不存在），因此
  **不计入** 5.1.0 的上游用例数，仅作差分骨架使用。

## 6. 查重反证与边界表（main tip，正式条目 542 条）

按主题检索 `knowledge/graph` + `knowledge/doc`（2026-10-03 重测于 tip `300641940`）：

```
git ls-tree -r --name-only origin/main -- knowledge/graph | grep -cE 'graph/E[0-9]{3}\.kv$'   # 542
git grep -il 'LDPL'          origin/main -- knowledge  # 0
git grep -il 'c++ 别名'       origin/main -- knowledge  # 0
git grep -il '编译器别名'     origin/main -- knowledge  # 0
git grep -il '运行期找编译器' origin/main -- knowledge  # 0
git grep -il 'wx-config'     origin/main -- knowledge/graph knowledge/doc  # 0
```

| 相邻条目 | 它的因果链 | 与本条的差异（反证） |
|---|---|---|
| E529 *Give OHOS CMake test_package recipes their own tool PATH* | 构建/测试期缺工具 → 给一条可用 PATH | 本条缺陷在**已安装包的运行期**；把 PATH 修好也没用（A4 组：`LDPL_CXX` 给了仍失败，因为上游不读 env，fork 的是字面量） |
| E405 *OHOS 下 python subprocess 裸名命令不搜索 PATH* | CPython 强制 `posix_spawn` 导致**解析方式**变了 | 本条是**名字根本不存在**（`command -v c++/g++/cc` 三个全空），换任何解析方式都失败；且失败方是 toybox `sh -c`，不是 python |
| E428 *pico-sdk test_package 的 Python 子脚本应接收 bin/pioasm 绝对路径* | 测试脚本侧把绝对路径当**参数**传进去 | 本条的路径消费点在**被适配程序内部**（`ldpl` 自己生成 `#include` 行），外部传参不可达，只能让包内常量运行期化 |
| E518 *Worker 的 git 缺 libz.so（RUNPATH 硬编码构建机路径）* | 同类「烧死构建机路径」，载体是 ELF RUNPATH / 动态加载 | 本条载体是**源码里的宏常量字符串**，`readelf -d` 看不到任何残留，只有运行期 fork 出的编译器报 file not found |
| 草稿 *DRAFT-jnoise-0.6.0-makefile-linkline-literal-cxx-name* | Makefile recipe 命令位写死 `g++`，`make CXX=` 与 env 都惰性 → 改成 `$(CXX)` | 同为「裸名 + env 惰性」家族，但 phase=linking、修法是变量化；本条 phase=**runtime**、fork 方是被适配程序本身，且额外有**随包资源定位**这一层（jnoise 无随包资源） |
| 草稿 *DRAFT-cohomcalg-0.32-makefile-gxx-override* | Makefile 把编译器放在变量里 → make 命令行可覆盖 | 正是本条的对偶：可覆盖 ⇒ 不需要补丁；不可覆盖 ⇒ 必须补丁。两者的判据都在「常量出现在哪个语法位置」 |

## 7. 证据与产物

- 配方：`archives/l/ldpl/5.1.0/{conanfile.py,conandata.yml,manifest.yaml,notes.md}`
- 补丁：`archives/l/ldpl/5.1.0/patches/0001-runtime-lib-location-and-cxx-override.patch`（53 行）
- 消费者用例：`archives/l/ldpl/5.1.0/test_package/test_ldpl.sh` 26 项断言，真机 `conan create` 退出码 0
- 矩阵/差分脚本与日志：`tools/ld8059_matrix.sh`、`tools/probes/ld8059_beh.sh`、设备 `~/work/psj/ld8059/`

## 8. 元信息

`draft: true` · `contributor_id: iKalous_OscarP` · `last_updated: 2026-10-03`
转正由主编执行；本 PR 不改 `knowledge/graph/`、`index.tsv`、`SUMMARY.md`、`SKILL.md`、`scripts/`、`ci/`。
