# dmenu 5.4 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile，无 configure）
- 编译日期: 2026-09-22
- 编译器: clang（OHOS aarch64，Conan toolchain conf 注入）
- 状态: built（本地 W3 验证通过；published 待 CI release 流水线确认）
- 适配窗口: DS-33（worktree ~/qzy/DS-33-dmenu-5.4，基线 upstream/main 48d9cee684）

## 编译步骤

1. W0 依赖发布核验（R35 口径 `conan download --only-recipe -r=ohpcd`）：
   `libx11/1.8.13`、`libxft/2.3.9`、`libxinerama/1.1.6` 均已发布 ✅
2. R47 语言预检：task=cpp / detected=c（兼容族）✅
3. conan create（conan-verify G2）内执行：
   - build(): `make CC=<conf 工具链> INCS='<依赖 include 目录>'
     LIBS='<依赖 lib 目录> -lX11 -lfontconfig -lXft' XINERAMAFLAGS= XINERAMALIBS= -j1`
     —— 命令行变量直接覆盖 config.mk 的 `INCS/LIBS` 两个聚合变量，
     绕开被烧死的 `X11INC/X11LIB/FREETYPEINC` 三个路径变量（零补丁）；
     `XINERAMAFLAGS=/XINERAMALIBS=` 置空 = 关闭上游自带的可选特性 Xinerama
   - package(): `make install PREFIX=<package_folder>
     MANPREFIX=<package_folder>/share/man -j1`
     （上游 install 目标用 cp -f/mkdir/chmod/sed，toybox 全部可用）
4. 消费者测试 test_package/test.sh：`dmenu -v` + PATH 断言 + stest 谓词断言

## 上游测试清点（R51，N_static=0 证据）

- tarball 无 tests/ 目录；源文件仅 dmenu.c/drw.c/util.c/stest.c + 头文件与脚本
- Makefile 目标：`all: dmenu stest`、`dmenu`、`stest`、`clean`、`dist`、`install`、
  `uninstall` —— **无 check/test 目标**
- `stest.c` 是 suckless 随包安装的文件谓词过滤器（dmenu_path 运行期依赖
  `stest -flqs +1 . "$PATH"` 枚举可执行文件），**不是针对 dmenu 的测试框架**
- ⇒ `N_static=0`，按规则以消费者测试补位（test.sh 内 4 组断言），
  清点证据同步写入 `test_package/MANIFEST.yml`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 首错 `make: cc: No such file or directory`（Error 127） | config.mk 烧死 `CC = cc`，OHOS 设备无 cc 别名 | make 命令行 `CC=<conf tools.build:compiler_executables 取得>`（R33 口径） |
| 2 | `make CC=clang` 次错 `dmenu.c:11:10: fatal error: 'X11/Xlib.h' file not found`（-I/usr/X11R6/include） | config.mk 烧死 `X11INC/X11LIB=/usr/X11R6`、`FREETYPEINC=/usr/include/freetype2`，交叉环境不可得 | 命令行覆盖聚合变量 `INCS/LIBS`，把 Conan 依赖（含传递）的 include/lib 目录全量注入；链接集保持上游原样（去 Xinerama 后为 `-lX11 -lfontconfig -lXft`） |
| 3 | conan create 报 `Version conflict: Conflict between libx11/6.4.0 and libx11/1.8.13 in the graph` | X11 生态双版本系：libxft/2.3.8-2.3.9 钉 libx11/1.8.13，libxinerama/1.1.5-1.1.6 钉 libx11/6.4.0（SONAME 风格兼容包，源码同为 libX11 1.8.10，见其 conanfile docstring）⇒ 同图硬冲突 | 禁用上游可选特性 Xinerama（config.mk 自注释"comment if you don't want it"）：`make XINERAMAFLAGS= XINERAMALIBS=` 置空 + 不依赖 libxinerama；gtk2 同因先例 `--disable-xinerama`。待生态统一 libx11 版本系后可版本后缀 5.4.1 重启用 |
| 4 | conan create 编译/链接/安装全过，但 test_package 运行期刷屏 `Error relocating .../bin/dmenu: FcCharSetCreate: symbol not found`；补 `LD_LIBRARY_PATH` 后变为 `Error loading shared library libfontconfig.so.1: (needed by .../bin/dmenu)`，而**同一目录里的 libX11.so.6 正常加载** | 设备侧加载器按 `.codesign` 签名做内容级放行（CI worker 不强制）：本机 clang 新链接的产物自带 ad-hoc 签名可加载，而 conan 从制品仓下载进本机缓存的依赖库签名来自他机构建链、不被本机信任 ⇒ 文件级拒载（直接 `exec` 该 .so 交叉印证报 `Operation not permitted`） | 只动**本机任务 CONAN_HOME 缓存副本**（可重建、与 CI 无关）：对 36 个被拦制品 .so 逐个 `llvm-objcopy --remove-section .codesign` + `LD_LIBRARY_PATH= binary-sign-tool sign -inFile <lib> -outFile <lib> -selfSign 1` + `chmod a+x`（E077 四步顺序）。配方与制品仓零改动；机制已沉淀为本 PR 的知识草稿（见下节） |

## B 判定（路径 B，create）

**本 PR 交付的草稿（同 stem 成对，随本 PR 原子提交）**：
`knowledge/drafts/DRAFT-dmenu-5.4-downloaded-deps-codesign-device-enforced.{kv,md}`

- **机制**：OHOS PC 设备侧强制校验共享库 `.codesign` 签名（CI worker 不强制）——
  conan 下载进本机缓存的依赖库签名不受本机信任时，消费者可执行文件运行期加载即被拒
  （musl 表现为 `Error loading shared library` / `symbol not found` 两种迷惑形态），
  对本机缓存 selfSign 重签即放行
- **签名**：`Error loading shared library libfontconfig.so.1: (needed by .../bin/dmenu)`
  + 同目录自编库放行 + 直接 exec 该 .so 报 `Operation not permitted`
- **复现**：conan create 后 `LD_LIBRARY_PATH=<依赖 lib 目录> <包内 bin>/dmenu -v`（设备实拍
  2026-09-22 DS-33）；判别三步（文件级 vs 路径级）见草稿 `verification_cmd`
- **修复后读数**：36/36 制品 .so 重签后 `dmenu -v` 输出 `dmenu-5.4`（rc=0），
  消费者测试 rc 由 2→2→0，`test dmenu 5.4: 4/4 checks PASS`
- **查重结论（措辞与工具输出对齐）**：`draft-review` 实测 TOP3 = E274 **0.59** /
  E316 0.47 / E186 0.46。**E274 的 0.59 已达到 merge-into 阈值 `_MERGE_TH = 0.55`**
  （`scripts/ohc/draft_review.py:29`；三态由 TOP1 分数按 `score >= _MERGE_TH` 得出，同文件
  138–143、169–171 行），工具据此**明确打印 `📌 预审建议: merge-into → E274`**，原文另附
  "疑似重复——建议与目标条目人工比对后合并或丢弃"。本包不否认这一读数，最终仍判 **create**，
  行使的是工具自身声明的口径——同一次输出末行原文为"⚠️ 以上建议仅为相似度计算参考；是否纳入
  正式知识库由人工审核决定"（另见 `SKILL.md:954` 对 `draft-review` 的说明"**纳入决策权在人工
  审核**，promote 命令不变"）。人工比对的实质依据：
  - **0.59 来自报错文本重叠，不来自机制重叠**：工具分项读数 sig=**0.89** / kw=**0.13** /
    cat=**0.33**，而 E274 的 `error_signature` 恰好就是 `Error loading shared library...needed
    by...` 与 `Error relocating...symbol not found`（`knowledge/graph/E274.kv:9-10`）——两条
    共享的是 musl 的这两句迷惑性报错文本，真正判别的关键词/类目维度得分都很低。
  - **E274**（janet 1.41.2）根因：Makefile 用 `-Wl,-soname,lib.so.X.Y` 出共享库，而配方
    `package()` 只复制 `lib.so`、未建版本化符号链接 ⇒ **运行期该 SONAME 文件在包里根本不存在**
    （`E274.kv:20-24`），解法是改配方补 `os.symlink`。**E316**（R/OpenBLAS）同族：
    `_prepare_relocatable_runtime` 只带走开发者符号链接、SONAME 实体缺失（`E316.kv:12`）。
  - **本条**恰好相反：SONAME 文件**存在且路径可达**——同一 `LD_LIBRARY_PATH` 目录下本机新链接的
    `libX11.so.6` 正常加载，同目录里 conan 下载的 `libfontconfig.so.1` 却被拒，直接 `exec` 该
    .so 报 `Operation not permitted`（见问题 #4）；这指认的是设备侧 `.codesign` 的**内容级签名
    门**（CI worker 不强制），与"文件/软链在不在"没有因果关系。解法也不同面：不改配方、不改
    制品仓，只对本机可重建的 CONAN_HOME 缓存副本 selfSign 重签。E077 只覆盖"配方自身产物打包后
    重签"，本条是"依赖侧制品在消费者测试运行期被拦"这一独立场景。
  - ⇒ 按"症状同、根因/解法不同 ⇒ create"口径申报。草稿 `## 判别要点（防止误诊）` 表
    （`knowledge/drafts/DRAFT-dmenu-5.4-downloaded-deps-codesign-device-enforced.md:44-50`）
    前两行"依赖没装/路径不对""库缺符号"即本条要与之区分的两种 SONAME 缺失族误诊形态，第三行
    区分 E077；该表未逐条点名 E274/E316，点名比对以本 notes 与下述工具留存输出为准。
    复核命令：`python3 scripts/ohc-run.py draft-review
    DRAFT-dmenu-5.4-downloaded-deps-codesign-device-enforced`（本窗 2026-09-23 逐字输出留存
    `~/tmp/uc2/主理-2-dmenu-notes/draft-review-verbatim.txt`）

**另有一条通用机制不随本 PR 提交**：suckless 裸 Makefile 烧死 `CC=cc` 与
`X11INC/X11LIB/FREETYPEINC` 系统路径 ⇒ build() 用 make 命令行变量覆盖 `INCS/LIBS`
注入 Conan 依赖路径（零补丁）。该机制适用于 st/slock/lsw/lsx/scroll/sprop/sent/tabbed
等同族包，已收编为工作区 B 草稿库通用池件
`经验文档/B草稿库/DRAFT-PKG-VER-suckless-baked-paths-makevar-override.{kv,md}`，
由真正撞上它的包各取一份随自己的 PR 提交（一 PR 一知识，AGENTS §6.2⑦ 第 1/3 条）。

## 源码修改

无补丁（patches 为空）。全部适配通过 make 变量覆盖完成，源码零改动。

## 依赖版本

- libx11/1.8.13（制品仓已发布）
- libxft/2.3.9（传递：fontconfig/2.18.3、freetype/2.14.3、libxrender/0.9.12、xorgproto/2025.1）
  —— `-lfontconfig` 直接出现在链接集但只作为 libxft 的传递依赖注入，
  `_dep_dirs()` 依赖 `self.dependencies.host` 的传递聚合语义；配方不显式 requires 它
- 不带 libxinerama（Xinerama 禁用，双版本系图冲突，见问题 #3）

## 验证结果

```bash
# conan-verify（W3）：conan create + G0-G4 + L2/L4/L5，8 道门禁
python3 scripts/ohc-run.py conan-verify dmenu 5.4
# 门禁逐项 PASS 见 reports/conan-verify-report.md；G2 全量日志 reports/conan-create.log
# （reports/ 属 AI 元数据、不随 PR 提交，故关键证据行抄录如下）
```

关键证据行（2026-09-22 设备实测，CONAN_HOME=~/tmp/ch/home-ds33-dmenu）：

- profile 注入：`tools.build:compiler_executables` 的 `c=/data/service/hnp/bin/clang`
- G2 conan create 通过，test_package 运行输出末行 `test dmenu 5.4: 4/4 checks PASS`
  （PASS 1 `dmenu -v -> dmenu-5.4`；PASS 2 dmenu_run/dmenu_path/stest 可解析；
  PASS 3 `stest -f` 普通文件匹配 rc=0；PASS 4 `stest -d` 普通文件不匹配 rc=1）
- 消费者测试 rc 轨迹 2 → 2 → 0（前两次为依赖库签名门拦载，见问题 #4）

**本机消费者测试通过的前置条件（如实披露）**：需先对本机任务 CONAN_HOME 缓存内被拦的
制品 `.so` 做 selfSign 重签（四步见问题 #4）。该操作只动本机可重建缓存，**配方与制品仓
零改动，不影响 CI**（worker 不强制校验签名，见 catch2/2.13.10-r0 先例）；机制与判别方法
即本 PR 交付的知识草稿。

## 注意事项

- dmenu 本体需要 X display 才能交互运行；消费者测试只用无头安全的
  `dmenu -v` 与 `stest`（真实执行 + 行为断言，R34 口径满足）
- `stest` 退出码语义：命中任一文件返回 0，否则 1（stest.c:108
  `return match ? 0 : 1`），错误返回 2——消费者测试据此断言
---

**编译结束**: 2026-09-23 00:43
**最终状态**: built
