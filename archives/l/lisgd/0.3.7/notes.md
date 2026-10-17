# lisgd 0.3.7 适配笔记

## 编译环境
- 构建系统: makefile（suckless 裸 Makefile，无 configure）
- 编译日期: 2026-10-03
- 编译器: clang（OHOS aarch64，Conan toolchain conf 注入）
- 状态: built（本地 W3 验证通过；published 待 CI release 流水线确认）
- 源码: `https://deb.debian.org/debian/pool/main/l/lisgd/lisgd_0.3.7.orig.tar.xz`
  （sha256 `4aa53e7a12de61019e0a08bd191297ac747706bdb8392c4cab8f6826a16c1e27`）

## 上游实物核对（2026-10-03，与任务书差异如实记录）

- tarball 解包 7 个文件：`.gitignore / LICENSE / Makefile / README.md /
  config.def.h / lisgd.1 / lisgd.c`
- **任务书称"2 枚 .c"，实物只有 1 枚 `.c`（lisgd.c）+ `config.def.h`** —— 差异记此
- Makefile 全文 49 行，关键行（逐行读）：
  ```
  L1  PREFIX = /usr          L4  LDFLAGS = -g      L5  LIBS = -linput -lm
  L7  X11INC = /usr/X11R6/include                 L8  X11LIB = /usr/X11R6/lib
  L10 ifndef WITHOUT_X11 → L11 CPPFLAGS += -I${X11INC} -DWITH_X11
                          → L12 LIBS     += -L${X11LIB} -lX11
  L14 ifndef WITHOUT_WAYLAND → L15 CPPFLAGS += -DWITH_WAYLAND
                             → L16 LIBS     += -lwayland-client
  L31 .c.o:  ${CC} -c ${CFLAGS} ${CPPFLAGS} $<
  L38 lisgd: ${CC} -o $@ ${OBJ} ${LDFLAGS} ${LIBS}
  L41 install: mkdir -p ${DESTDIR}${PREFIX}/bin + cp -f + chmod 755（+ man1）
  ```
- **无 `check` / `test` 目标**（`make -n check` 与 `make -n test` 均报
  `No rule to make target`）
- `lisgd.c` include 面：`<libinput.h>`（L3）、`#ifdef WITH_X11 → <X11/Xlib.h>`（L14）、
  `#ifdef WITH_WAYLAND → <wayland-client.h>`（L17）、`#include "config.h"`（L75）

## W0 依赖发布核验（R35 口径，B 机一手实测 2026-10-03）

| 依赖 | `conan download --only-recipe -r=ohpcd` | revision | `conan install --build=never -r=ohpcd` |
|---|---|---|---|
| libinput/1.26.2 | rc=0 | `a696130452076a2203ae79929c0a2fe3`（2026-09-27 14:04 UTC） | rc=0 |
| libx11/1.8.13 | rc=0 | `e3ce69008a37ca95d1f0918c47709057` | rc=0 |
| wayland/1.24.0 | rc=0 | `780e006283b9f3693a2267b486182de1` | rc=0 |
| （传递）xorgproto/2025.1 | — | — | rc=0，`Downloading binary packages` 实取到 package |

⚠ **`conan list xorgproto/*:*` 打印 `No packages found for this revision` 是假象**
（R35 已知：cnb.cool 搜索 API 对 binary 返回不完整），`conan install --build=never`
才作数 —— 本轮实测该包 binary 可正常下载，**未据此误判"依赖未发布"**。

三枚直接依赖的头/库布局（决定 make 变量怎么覆盖）：

| 头文件 | 实际位置 | 注入口 |
|---|---|---|
| `libinput.h` | `<libinput>/include/libinput.h` | `CFLAGS` |
| `libudev.h`（`libinput.h:35` 内部 include） | `<eudev>/include/`（**传递依赖**） | `CFLAGS`（`self.dependencies.host` 传递聚合） |
| `X11/Xlib.h` / `X11/X.h` | `<libx11>/include/` / `<xorgproto>/include/` | `X11INC` + `CFLAGS` |
| `wayland-client.h` | `<wayland>/include/` | `CFLAGS` |

## 编译步骤

1. `lang-preflight`：task=cpp / detected=c（兼容族）✅ 证据：`build_system=make`、
   `manifest=顶层 Makefile`、`source_stats=源文件 1 个（c:1）占比 100%`
2. W0 依赖核验（上表）
3. **四臂机制探针**（B 机一手，日志 `~/tmp/uc2/lisgd-0.3.7/08-arm-probe.log`、
   `12-p3.log`）：
   - **P1 上游原样 `make`** → `cc -c -I/usr/X11R6/include -DWITH_X11 -DWITH_WAYLAND lisgd.c`
     + `make: cc: No such file or directory` + `Error 127`（**烧死 CC=cc**）
   - **P2 `make CC=<clang>`** → `lisgd.c:3:10: fatal error: 'libinput.h' file not found`
     （**路径烧死**；`/usr/X11R6/include`、`/usr/include/libinput.h` 实测均不存在）
   - **P3 覆盖 `CC/CFLAGS/X11INC/X11LIB/LDFLAGS`** → 编译 1 warning（-Wswitch 枚举未全列）
     + 链接成功，产物 35392 B，`NEEDED = libinput.so.10 / libX11.so.6 /
     libwayland-client.so.0 / libc.so`，`make install` 落
     `usr/bin/lisgd` + `usr/share/man/man1/lisgd.1` —— **零补丁通过**
   - **P4 反证：命令行覆盖 `CPPFLAGS`** → `CPPFLAGS = -I<libx11>/include`，
     `-DWITH_X11` 与 `-I${X11INC}` **消失**（`+=` 被整段替换）
   - **P5 反证：命令行覆盖 `LIBS`** → `LIBS = -linput -lm`，
     `-L${X11LIB} -lX11 -lwayland-client` **消失**
   - **P6 `WITHOUT_X11=1`** → `CPPFLAGS = -DWITH_WAYLAND`、
     `LIBS = -linput -lm -lwayland-client`（**上游双后端开关有效**，退纯 Wayland 的备选路径）
4. `conan-verify`（G0-G4 + L2/L4/L5，内含 G2 `conan create` 从干净源码重建）
5. 消费者测试 `test_package/test.sh`：4 组断言（详见下方验证结果）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 首错 `make: cc: No such file or directory`（Error 127） | Makefile 烧死 `CC = cc`，OHOS 设备与 CI 均无 cc 别名 | make 命令行 `CC=<conf tools.build:compiler_executables 取得>`（R33 口径，conf 缺 `c` 键即 `ConanInvalidConfiguration`，不做字面量兜底） |
| 2 | `make CC=clang` 次错 `lisgd.c:3:10: fatal error: 'libinput.h' file not found` | Makefile 烧死 `X11INC/X11LIB=/usr/X11R6/*`；且交叉环境无系统 `libinput.h`/`wayland-client.h` | 命令行覆盖**路径变量** `X11INC/X11LIB` + 用 `CFLAGS` 携带全依赖 `-I` + `LDFLAGS` 携带全依赖 `-L`（**零补丁**） |
| 3 | 覆盖路径变量后首错变 `libinput.h:35:10: fatal error: 'libudev.h' file not found` | `libinput.h` 内部 include `<libudev.h>`，来自**传递依赖 eudev** | `_dep_dirs()` 走 `self.dependencies.host` 传递聚合（只聚合 direct requires 会漏 eudev） |
| 4 | 再错 `X11/Xlib.h:44:10: fatal error: 'X11/X.h' file not found` | `X11/X.h` 来自传递依赖 **xorgproto**，而首轮聚合时该包 package 尚未落缓存（`conan list` 还报 "No packages found" 假象） | 补跑 `conan install --build=never` 取回 xorgproto package 后重聚合；**判据用 conan install 不用 conan list（R35）** |
| 5 | ⛔ 若用 `CPPFLAGS=`/`LIBS=` 覆盖会静默丢掉 X11/Wayland（P4/P5 反证，无报错） | 上游 `CPPFLAGS += -I${X11INC} -DWITH_X11`、`LIBS += -L${X11LIB} -lX11` 是对聚合变量的 `+=`，命令行赋值整段替换 `+=` | 只覆盖**被 `+=` 引用的路径变量**（`X11INC/X11LIB`）与无 `+=` 引用的 `CFLAGS/LDFLAGS/CC`，绝不碰 `CPPFLAGS/LIBS`；已写入 conanfile docstring 与 manifest 注释 |
| 6 | **G2 conan create 首错**：`X11/Xlib.h:44:10: fatal error: 'X11/X.h' file not found`（日志同时印 `Skipped binaries: libffi/3.4.4, xcb-proto/1.17.0, xorgproto/2025.1, xtrans/1.4.0`） | conan 2 `Requirement.transform_downstream`（`internal/model/requires.py:329`）对 **`package_type=HEADER` 的传递依赖**置 `headers=False` ⇒ `Require.files` 为假 ⇒ `graph_binaries._skip_binaries` 把该节点标 `BINARY_SKIP`（conf `tools.graph:skip_binaries` 默认 True）⇒ 不安装、`package_folder` 为空、`self.dependencies.host` 聚合不到 xorgproto 的 include | **显式 `self.requires("xorgproto/2025.1")`**：该边成为 consumer 的 direct require ⇒ `req.direct and is_consumer` 成立 ⇒ 进 `deps_required` ⇒ `binary=Cache` 可聚合。实测三臂对照（`conan graph info`）：仅 libx11 ⇒ xorgproto `Skip`；加显式 requires ⇒ `Cache`；`-c tools.graph:skip_binaries=False` ⇒ `Cache`（后者会让 xtrans/xcb-proto 也下载，粒度过粗）。同仓 **113 份配方**同此写法 |

## 上游测试清点（R51，N_static=0 证据）

- tarball 7 文件**无 tests/ 目录、无 `*test*` 源文件**
- Makefile 目标仅 `all / options / .c.o / config.h / lisgd / install / clean`
  —— **无 check/test 目标**（`make -n check`、`make -n test` 均报
  `No rule to make target`，两条命令实跑 rc 非 0）
- 全包检索 "test" 仅命中 `lisgd.c:390` 一条行为注释
  （`// All fingers up - check if within millisecond limit, exec, & reset`）
  —— 非测试框架注册入口
- ⇒ `N_static=0`，按规则以消费者测试补位（test.sh 4 组断言），
  清点证据同步写入 `test_package/MANIFEST.yml`

## 运行期能力边界（如实披露）

B 机一手探测（`~/tmp/uc2/z75-lisgd/11-runtime-capability-probe.log` + 本轮复核）：

- `/dev/input` → `Permission denied`；`nodes=[] count=0`（无输入节点）
- `DISPLAY` / `WAYLAND_DISPLAY` / `XDG_RUNTIME_DIR` 全空，`/tmp/.X11-unix` 不存在
- sysfs 触摸能力扫描 `touch-ish= 0`

⇒ **lisgd 的"真实手势触发"在本平台无可执行环境**，消费者测试只断言**参数层与
显示探测层的确定性行为 + 运行期动态加载零错误**（这三点恰好覆盖本配方的核心价值：
二进制可运行、conan 依赖注入在运行期生效）。测试脚本先 `unset DISPLAY WAYLAND_DISPLAY`
再跑，使断言与运行机环境无关（否则 CI 若带显示变量会走 `wl_display_connect` 分支，
断言变成环境相关的假红/假绿）。

**依赖 `.so` 签名面（与 dmenu 5.4 #12032 的差异，如实记录）**：本包依赖图内的
制品 `.so` 共 **74 个全部带 `.codesign` 段**，但在 B 机设 `LD_LIBRARY_PATH` 后
**全部可加载**（`lisgd` 正常跑出业务诊断，无 `Error loading shared library` /
`Error relocating`），**未复现 dmenu 遇到的跨机拒载** ⇒ 本包不加重签 stage。
判据依据：B 草稿库该条草稿的更正说明已把"预构建 .so 跨机一律拒载"收窄为
libxft/fontconfig 两枚特定制品，且"同批远程下载的 libX11.so.6 被正常接受"。
若 CI 侧出现签名拒载，按返修路径处理（同仓先例 dmenu 5.4 的四步 selfSign）。

## B 判定（路径 B，create —— M18 首次配送落盘）

**本 PR 交付的草稿（同 stem 成对，随本 PR 原子提交）**：
`knowledge/drafts/DRAFT-lisgd-0.3.7-suckless-baked-paths-makevar-override.{kv,md}`

- **机制（M18，`B配送=M18`）**：suckless 系裸 Makefile 把 `CC=cc` 与
  `X11INC/X11LIB=/usr/X11R6/*` 系统路径烧死在 Makefile 里 ⇒ 用 **make 命令行覆盖
  路径变量**（而非聚合变量）把 Conan 依赖目录注入，**零补丁**完成适配
- **本包相对 dmenu 5.4 先例的实质差异（必须写准的机制点）**：dmenu 的 config.mk
  暴露的是聚合变量 `INCS/LIBS`，覆盖聚合变量即可；本包 Makefile 的 `CPPFLAGS/LIBS`
  是**聚合变量且用 `+=` 内联引用 `X11INC/X11LIB`** ⇒ 正确做法是**覆盖被引用的路径
  变量**（`X11INC/X11LIB`），让 `+=` 自动落位；**覆盖聚合变量反而会吞掉追加**
  （P4/P5 反证）。这是 M18 草稿边界分支的首例实物
- **签名（P1/P2 一手原文）**：
  `make: cc: No such file or directory`（Error 127）/
  `lisgd.c:3:10: fatal error: 'libinput.h' file not found`
- **查重**：`knowledge/graph/index.tsv` 对该机制零命中、`knowledge/drafts/`
  无 dmenu/suckless 族先例 ⇒ 非 hit 非空走（登记表 B判定栏已记）
- **`draft-review` 实测读数（2026-10-03，本窗逐字，工具 rc=0）**：
  - 质量预检三项全 ✅：`signature=✅  root_cause=✅  rec=✅`
  - 相似正式条目 TOP3：**E169 0.44**（sig=0.8 / kw=0.0 / cat=0.0）、
    **E217 0.37**（sig=0.67 / kw=0.0 / cat=0.0）、**E174 0.21**
  - 工具建议：`📌 预审建议: review-similar → E169  灰区——需人工判断与目标条目的关联性`
  - **本窗不否认该读数**（三态判据 `score >= _MERGE_TH(0.55)` 才是 merge-into，
    0.44 未触及阈值），仍判 **create**，人工比对依据如下：
    - **E169**（缺 GNU `argp.h` 头）——是「系统缺某个头文件」的平台缺件族；
      本条讲的是 **make 变量覆盖哪一层** 的构造性机制，与 E169 的签名重叠只来自
      `file not found` 这句公共文案（`sig=0.8` 而 `kw=0.0`/`cat=0.0` 已说明
      关键词与类目维度**零重合**）。
    - **E217**（CMake `install(FILES … DESTINATION include/…)`）——落点在
      CMake 打包路径，与本条 build 期路径注入不同阶段、不同构建族。
    - **E174**（缺 GNU `install` 命令）——即 M13 族（`DRAFT-lzip-1.24.1-…`），
      症状在 `package()` 的安装工具缺失，本条在 `build()` 的编译/链接注入。
      ⚠ **共享片段更正（W4 P3-1）**：E174 的共享签名片段是
      `directory` / `found` / `make:`（来自 `make: install: No such file or directory`
      与 `command not found`），其 `error_signature` **不含** `file not found`
      ⇒「三者重叠只来自 `file not found`」这一说法对 E174 不精确，须分开写：
      E169/E217 为 `file not found` 族、E174 为 `directory/found/make:` 族；
      三者 `kw`/`cat`/`phase` 维度均 0，实质结论（低于 `_MERGE_TH=0.55`、判 create）不变。
    - ⇒ 按「签名同、根因与解法不同 ⇒ create」口径申报；本条的新增价值是
      **覆盖 `+=` 内联引用形态下"覆盖错层会静默丢后端"** 这一半，M18 池件
      只写了注意事项、无正反探针，本包补齐 P3/P4/P5/P6 四臂。
  - 复核命令：`python3 scripts/ohc-run.py draft-review
    DRAFT-lisgd-0.3.7-suckless-baked-paths-makevar-override`
- **一 PR 一知识**：上游自带的 `ifndef WITHOUT_X11` / `ifndef WITHOUT_WAYLAND`
  双后端编译开关（可退纯 Wayland 后端）**不单独成条**，只记在此处与 manifest

## 源码修改

无补丁（`patches: {}`）。全部适配通过 make 命令行变量覆盖完成，源码零改动。

## 依赖版本

- `libinput/1.26.2`（直接）
- `libx11/1.8.13`（直接）
- `wayland/1.24.0`（直接）
- 传递（随图）：`libevdev/1.13.7`、`mtdev/1.1.7`、`eudev/3.2.14`、
  `xorgproto/2025.1`、`libxau/1.0.11`、`libxcb/1.17.0`、`libxdmcp/1.1.5`、
  `expat/2.8.2`、`libxml2/2.15.3` 等 —— 全部由 `_dep_dirs()` 聚合注入，配方不显式 requires

## 验证结果

```bash
# 门禁序列（W0 → W3）
bash ci/scripts/preflight_check.sh lisgd/0.3.7
python3 scripts/ohc-run.py recipe-search lisgd
python3 scripts/ohc-run.py conan-verify lisgd 0.3.7     # G0-G4 + L2/L4/L5，含 G2 conan create
python3 scripts/ohc-run.py finish lisgd 0.3.7 built
python3 scripts/ohc-run.py graph validate
```

消费者测试 `test_package/test.sh` 四组断言（B 机对照实测，日志见
`~/tmp/uc2/lisgd-0.3.7/`）：

- PASS 1 `command -v lisgd` → 包内 bin/ 已安装且 PATH 可解析
- PASS 2 `lisgd --bogus` → rc=1 且输出 usage 行
  `lisgd [-v] [-d /dev/input/0] [-o 0] [-t 200] [-r 20] [-m 400] [-g '…']`
- PASS 3 `lisgd -h` → rc=1 且输出 `option -h expects a value`
- PASS 4 `lisgd`（已 `unset DISPLAY WAYLAND_DISPLAY`）→ rc=1 且输出
  `Cannot detect display environment ($DISPLAY and $WAYLAND_DISPLAY unset); …`
  **且全程无 `Error loading shared library` / `Error relocating` / `symbol not found`**
  （= conan 依赖注入在运行期全部生效）

## 注意事项

### 一、上游归属与源（W4 P1-1 / P1-2 更正，PR 正文"补充说明"须与此同源）

- **真上游 = `https://git.sr.ht/~mil/lisgd`**（HTTP 200；Debian 签名 `lisgd_0.3.7-1.dsc`
  的 `Homepage` 字段即此；页面标题 *Libinput synthetic gesture daemon*，其 README 与
  tarball 内 README 逐字一致）。lisgd 是 suckless **风格**，但**不托管在 suckless.org**。
  本机复测：`git.sr.ht/~mil/lisgd` = **200**、`/refs` = **200**；
  `git.suckless.org/lisgd/` = **404**（根索引 200、仓库列表命中 0）、
  `dl.suckless.org/tools/lisgd-0.3.7.tar.gz` = **404**。
- ⛔ **上一版的错误结论（已更正，W4 P1-2）**：曾写「上游不发布 0.3.7 官方 tarball，
  五个 URL 全 404 ⇒ Debian pool 是唯一可得的原版分发件」。**该推论不成立** —— 五个 404
  全部打在**根本不托管本项目**的主机上，**404 ⇒ 上游不发布** 属结论超出证据范围。
- ✅ **官方归档确实存在**：refs 页对 0.3.7 直接给出
  `archive/dcdb22f7efd0db797c11055fbaa8dafd89c3d520.tar.gz`。本机实测 **HTTP 200、9277 B、
  sha256 `f4fa03bf4777f7ebbf2ee4a7ddc9ea9637082c1c027d21a68e3576450b9e338e`**、
  顶层目录 `lisgd-dcdb22f7efd0db797c11055fbaa8dafd89c3d520/`、**7 个文件（含 `.gitignore`）**。
- ✅ **本 PR 仍用 Debian `.orig`（裁决：不换源，只更正理由与宿主）**：
  `4aa53e7a12de61019e0a08bd191297ac747706bdb8392c4cab8f6826a16c1e27`、8664 B、
  顶层目录 `lisgd-0.3.7/`、**7 个文件（同样含 `.gitignore`）**。
  **本机解包逐文件比对：7/7 文件 sha256 完全一致 ⇒ 两者是同一上游代码的两种分发形态**，
  差异只在顶层目录名、压缩格式与字节数。
  - **仍选它的理由（均可核）**：① Debian 签名 `lisgd_0.3.7-1.dsc` 的 `Checksums-Sha256`
    记 `4aa53e7a…a16c1e27 8664 lisgd_0.3.7.orig.tar.xz`，与本包 sha256 逐字一致，且
    `.orig` 与 `.debian.tar.xz` 分离 ⇒ pristine upstream 认证；
    ② 同仓先例充分：磁盘上 **479** 份 `conandata.yml` 使用 `deb.debian.org`
    （含本包自身，即已合入 **478** 份）；
    ③ 属框架 PF7 的规则内例外，逃生口文案原文见 `scripts/ohc/preflight.py:424`
    「确属官方托管例外须 PR 说明并 --no-preflight 跳过」。
  - **不换源的代价理由**：sr.ht 归档顶层目录是 `lisgd-dcdb22f7…/` 而非 `lisgd-0.3.7/`，
    换源会同时改 sha256 与顶层目录名 ⇒ 牵动 `source()` 解包逻辑、须重跑 W3、并作废本轮
    W4 审计，收益不抵代价。
  - ⚠ **与派单拟稿的一处出入（我按实测写，未照抄）**：派单拟写「(b) Debian 侧为 7 条目
    release 形态、不含 `.gitignore` 等仓库杂项」。**实测该句不成立** —— Debian `.orig`
    与 sr.ht 归档**都含 `.gitignore`、都是 7 个文件**；W4 判决件自己的 P0 读数也写明
    「tarball 实测 7 文件（.gitignore/LICENSE/Makefile/README.md/config.def.h/lisgd.1/lisgd.c)」。
    为免再造一条可被第三方一次推翻的声明，本节改写为「逐文件哈希一致 ⇒ 两种分发形态」。

### 二、框架硬闸披露：PF7 **与** PF9 两条都必须进 PR 正文（W4 P2-4）

`python3 scripts/ohc/preflight.py <worktree> upstream/main HEAD` **实跑 RC=1、3 条硬闸**
（改写本节前复跑一次，行号为当前实测值）：

- **PF9 分支/路径闸 ×1** —— 点名 3 个 4 段路径
  `archives/l/lisgd/{README.md,commands.json,manifest.yaml}`，判「变更路径缺版本目录层」。
  **已知误报**：这三件是 R38/PF8 强制的**软件级**文件（`commands.json` 必须放软件级，
  `archives/<字母>/<包>/commands.json` 本就是 4 段），按 PF9 的期望反而不该存在。
  **对照实验（本机自测，非转述）**：对 **valkey**（CI 已绿、已提审、`unresolved=0`）跑同一
  `run_preflight` ⇒ **同样报 PF9、同款三个软件级文件**
  （`archives/v/valkey/{README.md,commands.json,manifest.yaml}`）⇒ 该闸对含软件级文件的
  合法配方恒发，属 R38 要求与 PF9 要求自相矛盾
  （依据：经验库 12a §12.82、`反馈/pending/主理-1-PF8与PF9自相矛盾…-0930.md`）。
- **PF7 源URL闸 ×2** —— `conandata.yml:43`（`sources.url`）与 `manifest.yaml:23`
  （`source.url`），`deb.debian.org` 被判「Debian 下游重打包源」；理由与例外见第一节。
- **处置（裁决已定）**：两闸都走 `--no-preflight` + PR 正文「补充说明」**同时披露 PF7 与 PF9**。
  **漏披露会把假阳性变成真违规**（本节与 PR 正文、两份 manifest 必须三处同源）。

### 三、finish 三条非阻塞红字的真实定性（W4 P3-3；接手者/CIW 不必重查）

`finish` 最终 **EXIT_CODE=0 / `finish_success`**，打印的 `失败步骤: step5b, step7, step8`
三条**均不阻塞**，归因如下：

1. **step7（W2 PR 原子性）❌ = 基线过期假阳性**：`check_pr_atomicity` 硬编码
   `origin/main...HEAD`，而 fork `origin/main` 落后 `upstream/main` **3967 提交** ⇒ 算出
   **27899 个文件**、含 5 个框架文件（`.gitignore`、`SUMMARY.md`、`ci/config/build_timeouts.txt`、
   `knowledge/graph/index.tsv`、`knowledge/graph/pre-scan-rules.yaml`）与「配方文件变更 27894 个」。
   **真口径 `upstream/main...HEAD` = 12 个文件、框架文件 0 个、软件包 1 个** ⇒ 真实 PR 完全原子。
   （该工具不吃 `JUNK_PR_DIFF`，本链未改它；已由主理立档 `⛔ 无通道·仅存档`。）
2. **step5b（W5 知识完整性）❌ = 存量他包问题**：`knowledge/graph/{E219,E253,E305}.kv` 的
   `root_cause`/`rec_approach` 为空；`git diff upstream/main -- 三文件` **输出为空**
   ⇒ 与 upstream/main 逐字一致，非本包引入（动它 = 改基线 + 动框架文件，会破 W2）。
3. **step8（submit 就绪）❌ = `.staging-verified` 未生成**。**归因（W4 P3-2 修正）**：
   `driver.py` 的 `_step8_staging` 对该标记是**无条件 `mark.write_text(report)`**
   （哪怕 `verified=0` 也会写出，`EXCLUDE_LIST` 仅在有失败可执行文件时才写）；而本包目录下
   既无 `EXCLUDE_LIST`、日志里也没有任何 `[8/14] Staging 验证` 步骤 ⇒
   **真因是本链没跑 driver Step8**，**不是**「lisgd 无 `--version` 写不出」。
   （lisgd 无 `--version` 属实，但那是 L2 判 `skip`、quality G2 只给 ⚠️ 的事，与本标记无关。）
   实质影响为零：`.gitignore:64` 与 `:255` 已忽略它、`submission.py` 全文零引用、
   finish 只记 gate_warnings 并给 Step10 一条 ❌。
   同段另一条 `gen_summary` 报 `'str' object has no attribute 'append'` 是**框架工具 bug**
   （`scripts/ohc/summary.py:89` 的 `data.setdefault(current_list_key, []).append(item)`，
   当该键已是标量字符串时炸；本机复现指向他包存量 `archives/q/qpdf/*` 的 manifest，
   **lisgd 自身解析全部通过**），finish 捕获为警告、不阻塞。
4. 附带一条 finalize 警告：`⚠️ notes.md 无对话记录`（`finalize_archive.py` 查
   `### 对话 #`，RC=2 计 1 个一致性问题）—— **presubmit 实查的是收尾块的「最终状态」**，
   本文件末尾已有该块，故不阻塞。

### 四、其它

- 本包是 **CLI 工具包**（`package_type=application`，bindirs=`bin`）⇒ 软件级
  `commands.json` 已建（R38 / 门禁 L0k）
- 平台能力墙：无 `/dev/input`、无显示环境 ⇒ 真实手势触发不可验，边界已写入
  `test_package/MANIFEST.yml` 与「运行期能力边界」一节
---

**编译结束**: 2026-10-03 20:35
**最终状态**: built
