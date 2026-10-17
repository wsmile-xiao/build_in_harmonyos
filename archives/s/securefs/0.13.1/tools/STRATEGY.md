# 处理策略：适配前置三类风险

> 适用对象：**所有**「上游源码发布包 + 自有构建脚本」的 C/C++ 三方库，
> 不限于本样例库。三类风险都可在**动手适配之前**静态检出，且都有机械、可复现的处置动作。
>
> 检出工具：`tools/prescan_risks.py`
> 复现脚本：`tools/reproduce.sh`（干净环境、无缓存、日志落文件，CI 可直接跑）
> 样例库：securefs 0.13.1（三类风险全中，见 `notes.md` 与 `reports/`）

---

## R1 — 构建脚本声明的最低 CMake 版本 < 3.5

**现象（CMake 4.x 上的原始报错，实测原文）**

```
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
  Update the VERSION argument <min> value.  Or, use the <min>...<max> syntax ...
  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
```

**根因**
CMake 4.0 起移除对 `cmake_minimum_required(VERSION <3.5)` 的兼容层，这是**硬失败**
（不是警告）。老库（2016 年前后定稿的 CMake 工程）大量中招，与 OHOS 无关，
但会让任何干净 CI 在第一行就挂掉。

**识别**

```sh
python3 tools/prescan_risks.py <源码目录> --rules R1      # 命中即报告 file:line
```

**处置**

| 方案 | 做法 | 适用 |
|------|------|------|
| A（首选，本样例采用） | 补丁把 `cmake_minimum_required(VERSION 3.0 FATAL_ERROR)` 抬到 `3.10` | cmake 3.x/4.x 通吃，行为等价（3.10 早于任何在用工具链） |
| B（零侵入） | 配置时传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` | 只想快速验证、或不便改源码时；**必须走命令行 `-D`**，写在 toolchain 文件里无效——`cmake_minimum_required` 在 `project()` 之前执行，早于工具链文件加载 |

> 反例提醒：把 `3.0` 直接改成 `4.0` 是错误处置——会顺手丢掉 3.x 用户与
> 老 `CMAKE_POLICY` 语义，属于把兼容性问题转嫁给下游。

**验证**：`cmake -S <src> -B <build>` 进入正常 Configure（不再在第一行 FATAL_ERROR）。

---

## R2 — 上游发布包缺 git submodule 源码

**现象**
源码解包后 `add_subdirectory(external/cryptopp)` 报目录无 `CMakeLists.txt`；
或编译时 `fatal error: 'cryptopp/secblock.h' file not found`。

**根因**
`git archive` / GitHub 的 `archive/refs/tags/*.tar.gz` **只打包被 git 跟踪的普通文件**，
子模块在父仓库树里是 gitlink（mode `160000`），不含内容。凡 `.gitmodules` 声明的路径，
在发布包里必定是空目录。上游 CI（`git clone --recursive`）不会暴露这个问题，
所以上游发版时也不会发现。

**识别**

```sh
python3 tools/prescan_risks.py <源码目录> --rules R2      # 报出每个空/缺的子模块路径与 URL
# 取「父仓库 tag 上固定的子模块 commit」（gitlink 值）：
git -C <父仓库克隆> ls-tree <tag> external/               # 看到 160000 commit <sha> <path>
```

**处置（首选：Conan 多源清单）**

1. 用上一步的 `ls-tree` 结果拿到每个子模块的 **固定 commit**；
2. 按 commit 生成官方不可变 archive URL：
   `https://github.com/<owner>/<repo>/archive/<sha>.tar.gz`
3. 本地下载并计算 `sha256`，逐条写进 `conandata.yml` 的 `sources` 多源清单；
4. recipe 的 `source()` 用 `conan.tools.files.get()` 把每个子模块解到
   `external/<name>/`（`strip_root=True`），`sha256` 由 Conan 强校验。

**为什么必须按 commit 而不是 tag/分支**：tag 与分支可被上游移动/删除，而 commit
（gitlink 值）与内容哈希绑定，是唯一能保证「与上游发行时点的源码逐字节一致」的引用。

**备选方案与代价**

| 方案 | 代价 |
|------|------|
| `git clone --recursive` 取源码 | CI 需要 git 网络与完整克隆，慢且引入非确定性；仅作本地排查 |
| 用 Debian/发行版重打包源码 | 违反「源码 URL 必须官方源」，且版本可能被改写 |
| 让 recipe 依赖成品库（如 cryptopp/8.9.0）替换内嵌子模块 | 改变了上游构建语义（内嵌版本常与上游不兼容），且把可移植性问题转移成依赖可用性问题 |

**验证**：`conan create` 的 source 阶段无 sha256 报错，`external/<name>/` 内有源码；
configure 阶段 `add_subdirectory` 通过。

---

## R3 — 构建脚本硬编码系统库探测路径

**现象**

```cmake
find_path(FUSE_INCLUDE_DIR fuse.h PATHS /usr/local/include)
find_library(FUSE_LIBRARIES fuse PATHS /usr/local/lib)
```

干净构建机 / 交叉编译环境里 `/usr/local` 下没有该库 →
`FUSE_INCLUDE_DIR-NOTFOUND` → 编译 `fuse.h: No such file or directory`。
（更坏的情况：构建机 `/usr/local` 恰好**有**该库，于是错链宿主 x86_64 库，
交叉编译产物不可用——这类问题在 CI 上不报错，在设备上崩。）

**根因**
`PATHS` 里写死绝对前缀后，CMake 的 `find_*` 不再走 `CMAKE_PREFIX_PATH` /
`CMAKE_FIND_ROOT_PATH` / sysroot 搜索链；而 Conan 交叉编译的依赖前缀
（`<conan cache>/p/<pkg>/<id>/p`）**既不是** `/usr/local`，也**不在** CMake 的
默认搜索路径里。

**识别**

```sh
python3 tools/prescan_risks.py <源码目录> --rules R3
# 人工复核要点：命中的行是否真的用于「探测/链接系统库」，而非纯注释或文档示例
```

**处置（本样例采用的组合）**

1. **补丁**：去掉写死的 `PATHS`，让 `find_path`/`find_library` 恢复标准搜索链；
   同时保留 `FUSE_INCLUDE_DIR`/`FUSE_LIBRARIES` 作为可被 `-D` 覆盖的缓存变量（上游原本就是）。
2. **recipe 注入**：在 `generate()` 里用 `CMakeToolchain.variables` 把依赖的
   `cpp_info` 路径显式传下去，依赖走**包私有前缀**，不碰任何共享 `/usr/local`：

```python
dep = self.dependencies["libfuse"]
tc.variables["FUSE_INCLUDE_DIR"] = dep.cpp_info.includedirs[0]
tc.variables["FUSE_LIBRARIES"] = dep.cpp_info.libs[0]  # 或 full path
```

> 边界（务必遵守）：注入目标必须是**包私有前缀**（Conan 的依赖包目录或
> `build_folder` 下的私有目录）。任何「把依赖装进 `/usr/local` 再让构建脚本去
> 那里找」的做法都会在共享文件系统的 worker 上造成互相污染，是本类问题的反面模式。

**验证**：configure 阶段 `FUSE_INCLUDE_DIR` 指向 Conan 依赖目录；
`--graph`/构建日志中不出现宿主 `/usr/local` 的身影；编译通过且产物为 aarch64。

---

## 三类风险的共同处置原则

1. **先扫后做**：适配开始前跑 `prescan_risks.py`，把「必然失败」的问题在动手前变成清单。
2. **引用不可变**：源码一律按 commit + sha256 引用（R2），版本/分支引用只能用于排查。
3. **依赖只从包来**：任何依赖路径都从 `self.dependencies[...].cpp_info` 取，
   绝不写死系统前缀（R3），也绝不安装到共享前缀。
4. **补丁最小化**：优先用工具链变量/命令行开关；非改源码不可时，改一行是一行，
   并用 `refresh-patch --auto` 生成补丁（R1、R3 各一条）。
