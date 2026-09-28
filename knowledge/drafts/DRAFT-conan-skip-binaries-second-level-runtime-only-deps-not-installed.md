# conan skip-binaries：纯消费者场景二级 runtime-only 依赖不安装，运行时 loader 必失败

> 知识草稿（与 kjumpingcube 26.04.0 归档同 PR 交付）。
> Path: B（Curator 判定 A+B，配额 2/2）｜域: 依赖闭包｜等级: L1（主条）。
> 来源：kjumpingcube 26.04.0 适配，权威 CI（ci/conan/build_and_test.sh，
> ohos-aarch64）attempt5 失败定位、attempt6 修复后 PASS。
> 场景：KXmlGui GUI 应用（纯消费者）经 libkdegames/26.04.0.1 间接消费
> openal-soft（libopenal.so.1）与 libsndfile（libsndfile.so.1）。

## 现象

- `conan create` 的安装计划明确列出：

  ```
  Skipped binaries
      libiconv/1.17, libsndfile/1.2.2, openal-soft/1.25.2, openssl/3.5.6.1,
      xz/5.6.2, zlib/1.3.2, ...
  ```

  安装清单（42 项，逐项 "Already installed!"）中没有 openal-soft 与
  libsndfile。
- test_package 阶段执行打包出的 `bin/kjumpingcube` 时 musl loader 报：

  ```
  Error loading shared library libopenal.so.1: (needed by .../p/lib/libKDEGames6.so)
  ```

  随后退出码 127。

## 根因（机理链）

1. **conan 的 skip 判定**：应用（纯消费者）的 CMake 链接行里只有
   `libKDEGames6.so` 这类中间共享库；openal-soft/libsndfile 只是中间库
   自身 `DT_NEEDED` 的运行时件，conan 的图分析看不到共享库二进制内部的
   NEEDED，判定"该二级包对最终消费者不可见"。
2. **skip 的后果在安装决策层**：被 skip 的包不下载、不构建、不安装——
   重跑 `--build=missing` 无效，因为这不是缓存缺失而是"判定不需要"。
   即便本地缓存存在**其他 package_id** 的同名包二进制，test graph 里该
   节点的 `package_folder` 仍为 `None`（id 对不上且 skip 使 conan 不去
   绑定/取回）。
3. **运行时暴露**：test_package 执行打包二进制时，musl loader 沿
   `libKDEGames6.so` 的 `DT_NEEDED`（`libopenal.so.1`）在
   `LD_LIBRARY_PATH` 里找不到任何提供者——因为提供者的包目录压根没进
   graph——loader 报 `Error loading shared library`，退出码 127。

## 修复（配方层双处声明）

- **主配方** `requirements()` 显式直连运行时闭包：

  ```python
  self.requires("openal-soft/1.25.2")
  self.requires("libsndfile/1.2.2")
  ```

  直接依赖永远不会进 Skipped binaries，conan create/install 会为其下载/
  构建二进制。版本与中间库 recipe 所钉版本一致（均为 libkdegames 所
  require 的版本，皆已发布）。
- **test_package** `requirements()` 同样复声明。两个原因：
  1. test graph 会把被测包的二级依赖标记 skip（遍历
     `self.dependencies` 时这些节点 `package_folder=None`），复声明是
     配方层唯一的 unskip 手段（`libkdegames/26.04.0.1` 的 test_package
     即同一先例，其 test_ohos 的 openal 播放断言依赖于此）；
  2. test_package 需要把这些包的 `lib/` 目录收进 `LD_LIBRARY_PATH`
     闭包供 loader 解析。

## 适用边界

- 触发面：**纯消费者 + 中间共享库 + 二级 runtime-only 依赖**。GUI 应用
  消费音频/多媒体后端类共享库是最典型形态（openal、sndfile、gstreamer
  runtime 插件包等）。
- 不触发：二级依赖同时被应用直接链接（CMake 链接行出现即非
  runtime-only）；纯静态图（loader 不做二级 NEEDED 解析）。
- 识别要点：看到 `Error loading shared library libX.so.N (needed by
  <中间库>.so)` 且 libX 的 recipe 在图里可见、却出现在安装计划的
  "Skipped binaries" 段时，先对照安装清单确认"未安装"，再按本条修复，
  不要往下载源/缓存损坏方向排查。

## 验证（自包含复现，不依赖本 run 日志）

1. 构造三级最小图 `app -> mid(shared) -> base(shared)`：app 仅链接
   mid，mid 的 `.so` DT_NEEDED `libbase.so`；
2. `conan create app --build=missing -pr:h=<profile> -pr:b=<profile>`：
   断言输出含 `Skipped binaries` 且列出 base，app 的 test_package 报
   `Error loading shared library libbase.so`；
3. app 配方追加 `self.requires("base/1.0")` 后重跑：两处失败消失，
   出现 `base/1.0: Already installed`。
4. 在制品仓内的判定命令：`conan list "openal-soft/1.25.2" -r=ohpcd`
   （确认已发布，排除"源缺失"假象）。

## 查重差异（引用编号以 worktree 内 knowledge/graph 实际存在条目为准）

- **E019**（ld/runtime：`error while loading shared libraries`）：同一
  loader 失败**症状面**，但其根因层是链接闭包/搜索路径问题；本条目的
  根因层在 **conan 图解析与安装决策（skip-binaries）**——图里"看得见
  recipe、装不出二进制"，属安装决策缺口而非路径缺口。部分相关，机制
  不同，新增。
- **E088**（python ImportError / Error loading shared library）：python
  扩展模块场景的 loader 失败，同样是症状面重叠；不涉及 conan 安装
  决策。不覆盖本条。
- **E298**（Conan test_package 的显式运行与环境）：覆盖"test_package
  运行需要显式构造环境"的主题（与本 run 的内联环境变量实践互补），
  但未涉及"哪些依赖会因 skip 根本不在 graph 里"这一安装层问题。
  方向互补，机制不同，新增。
- 图谱内未命中任何以 skip-binaries / 二级 runtime-only 缺口为主题的
  条目。

## 历史证据（run 局部路径，仅溯源用）

- run `kjumpingcube-26.04.0`：
  - `ci-attempt5.log:796` — `Error loading shared library libopenal.so.1 (needed by .../libKDEGames6.so)`；
  - `ci-attempt5.log:305`、`ci-attempt5.log:740` — 主图与 test 图的
    `Skipped binaries` 段（均含 openal-soft/libsndfile）；
  - `ci-attempt6.log` — 主配方直连 require 后安装清单出现
    `openal-soft/1.25.2: Already installed`，测试 PASS。
