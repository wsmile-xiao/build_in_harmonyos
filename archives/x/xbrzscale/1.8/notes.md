# xbrzscale 1.8 适配笔记

## 编译环境

- 构建系统: makefile（上游为手写 Makefile，无 configure/CMake/Meson）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（来自 Conan conf `tools.build:compiler_executables`；目标 aarch64-linux-ohos）
- 状态: built（首轮工作树完成；真机预检尚未执行，通过后更新为 published）

## 版本与源码说明

- 上游仓库无 tag。版本 1.8 锚定官方提交 `ef36908831c058df7a202c8175d575a1fdfaf156`
  （"#11 Updated xbrz to 1.8"，2020-11-11，内嵌 xBRZ 升级到 1.8）。
- conandata.yml 使用官方 `github.com/atheros/xbrzscale/archive/<sha>.tar.gz`
 （R39/PF7 合规；CI 自动追加镜像 fallback）。
- sha256 `1927f7e5a07e…8145b` 为 github 与 codeload 双 URL 下载同字节核验值（41,553 字节）。

## 编译步骤

上游 Makefile 步骤的显式等价实现（`conanfile.py build()`，R33 合规）：

```bash
cxx -std=c++17 -DNDEBUG -c xbrz/xbrz.cpp -o xbrz/xbrz.o <SDL includes> -D_REENTRANT
cxx -std=c++17 -c libxbrzscale.cpp -o libxbrzscale.o <SDL includes> -D_REENTRANT
cxx -std=c++17 -c xbrzscale.cpp -o xbrzscale.o <SDL includes> -D_REENTRANT
ar qc libxbrzscale.a libxbrzscale.o xbrz/xbrz.o
cxx -o xbrzscale xbrzscale.o libxbrzscale.a -L<deps> -lSDL2_image -l<transitive> -lSDL2 -l<system>
```

显式编译的原因：上游 Makefile 硬编码 `g++` 并用反引号 `sdl2-config`，
无视 CC/CXX/CFLAGS/LDFLAGS，直接 `make` 无法注入 Conan 工具链，
故按相同源文件与相同编译选项逐条执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无版本 tag，源码 URL 与版本对应关系不明 | 仓库仅有 master 分支，1.8 为 Debian 包版本 | 溯源 GitHub 提交历史，定位 `#11 Updated xbrz to 1.8`（ef36908）为版本锚点；conandata 注释写明考证过程 |
| 2 | `make` 无法传递 OHOS 工具链 | Makefile 硬编码 g++，不支持变量覆盖 | build() 显式编译（见上节），编译器取自 conf，flags 聚合自 self.dependencies；无补丁 |
| 3 | 静态链接需 transitive 依赖顺序 | libSDL2_image.a 引用 SDL 符号；SDL2main 不需要 | 链接顺序 SDL2_image → 其他共享 transitive → SDL2 → system libs；排除 SDL2main/SDL2test（上游自带 main） |
| 4 | PNG 读写后端不确定性 | 默认 SDL2_image 变体可能走 STB 回退 | 依赖改用 libpng 后端的 sdl2_image/2.6.0.1（+ sdl2/2.30.10.1），与 AssaultCube 已验证组合一致 |
| 5 | 上游无测试套件 | Makefile 无 check/test 目标，无 tests/ 目录 | test_package 自建 9 端到端用例 + 6 库断言；MANIFEST 走 no_tests + manual_audit；build() 内置防腐败守卫（上游新增测试目标即失败提醒更新审计） |
| 6 | 真机预检 compile 失败：`cmake/4.4.3 build() line 35 KeyError: 'OHOS'`（2026-09-20；下轮预检证实 RREV 全部命中 ohpcd，该边已消除） | 预检 remote 顺序 conancenter 在前（CI 则禁用 conancenter）：传递闭包的裸版本 libpng/1.6.58、libjpeg-turbo/3.2.0、libwebp/1.6.0、zlib/1.3.2 落到 CCI 配方，其 `tool_requires("cmake")` 拖入 CCI cmake/4.4.3（conandata 无 OHOS 源码条目）；同时 sdl2_image/2.6.0.1 报主二进制缺失需源码构建 | requirements() 加版本不变的 ohpcd RREV pin（override=True，保持 sdl2_image package_id）：libpng/1.6.58#d25df07a、libjpeg-turbo/3.2.0#5ed08e7f、libwebp/1.6.0#8b273a51（ayatana-ido/pycairo/libtiger 先例，ohpcd API 实测单值）＋ 仓库独有 zlib/1.3.1.1（vips/gtk4/libcoverart 先例；即已发布 libpng/1.6.58 二进制所依赖的版本）。闭包回到零 tool_requires 的本仓硬化配方（bare cmake＋ohos.toolchain/autotools），cmake 工具边整枝移出 |
| 7 | pin 后新失败：`build()` 内 `TypeError: ... NoneType`（2026-09-20 预检：RREV 全部命中 ohpcd，cmake 边已消除，xbrzscale 自身构建期 `_dep_abs_dirs` 在 `os.path.join(dep.package_folder, entry)` 崩溃） | `self.dependencies.values()` 含无包路径节点（override-only/未解析节点 `package_folder` 为 None；fceux 先例亦载明 override 节点无直接边），原代码无条件 join | `_dep_abs_dirs`（主包）与 `_include_dirs`/`_link_flags`（test_package）统一加守卫：`package_folder` 为空则跳过该节点（主包侧打 info 日志指明节点，便于下轮日志确认身份），条目非字符串/空同样跳过；未删减任何依赖 flags 生成逻辑——真实节点的头/库路径照常聚合 |
| 8 | pin＋守卫后新失败：`build()` 首条编译命令 `/bin/sh: /data/service/hnp/bin/clang++: inaccessible or not found`（Error 127；flags 已正确聚合出全部 -I/-L/-l） | profile conf `tools.build:compiler_executables` 写死的 SDK 绝对路径在执行预检的 worker 上不可访问（隔离 worker 挂载路径与 CI 不同；opencsg/libcoverart/fceux 先例均载明此情形） | 主包与 test_package 各加 `_resolve_tool`：conf 路径仅在文件存在时采用，否则经 `shutil.which` 走 PATH 回退（hmbs/profile 已前置 worker 工具目录；命中回退时打 info 日志，找不到则保留原值不断言）；`ar` 同理（llvm-ar→ar）。未改动任何编译命令与 flags 逻辑 |
| 9 | 上轮之后新失败：test_package `test_lib.cpp:11 fatal error: 'SDL2/SDL.h' file not found`（2026-09-20 预检；主包 build 已通过，-I 含 sdl2 系路径但按 `<SDL2/SDL.h>` 拼写找不到） | 测试源用 `<SDL2/SDL.h>` / `<SDL2/SDL_image.h>` 拼写，要求 `-I<sdl2>/include` 下有 `SDL2/SDL.h`；而 sdl2_image/2.6.0.1 的 package_info 为 `includedirs=["include/SDL2","include"]`（SDL_image.h 做 `#include "SDL.h"`，消费者需 `include/SDL2` 在路径上），其自带 test_package 亦用 `<SDL.h>` / `<SDL_image.h>` 拼写（本仓实证）。两种拼写各需不同的 -I 前缀，单拼写在 worker 的实际头布局下不可移植；且 test_package 仅 `requires(tested_reference_str)`，隐式依赖透传 | 生产侧保持 `cpp_info.requires=[sdl2_image::sdl2_image,sdl2::sdl2]`（透传不变）；消费侧显式声明对齐的 `sdl2/2.30.10.1` + `sdl2_image/2.6.0.1`（与主包同版本），测试三源文件改 `__has_include` 双拼写回退（优先 `<SDL2/...>`，缺失则 `<SDL.h>` / `<SDL_image.h>`），不断言/计数未动 |

## 源码修改

无补丁（`patches: {}`）。上游源码无需 OHOS 修改。

## 依赖版本

- sdl2/2.30.10.1（W0：在树内；制品仓发布状态以后续 PF4 门禁为准）
- sdl2_image/2.6.0.1（libpng 后端；连带 libpng/libjpeg-turbo/libwebp transitive）
- 传递闭包 CCI 竞争 pin（override=True，版本不变）：libpng/1.6.58#d25df07a、libjpeg-turbo/3.2.0#5ed08e7f、libwebp/1.6.0#8b273a51（ohpcd RREV）、zlib/1.3.1.1（仓库独有；即已发布 libpng 二进制所依赖版本）
- 构建期宿主工具：`ar`（取自 conf，回退 llvm-ar）、`sh`

## 验证结果

首轮（本轮）：工作树完成，未执行真机验证。以下待 HMBS 真机预检回填：

```text
# test_package（sh test_xbrzscale.sh）：目标 9/9（CLI 校验 3、夹具 2、文件放大 3、库 API 1）
# test_lib 内部断言：目标 6/6
# 上游测试：no_tests（无套件，见 MANIFEST 审计）
```

真机通过后还需补做（记录于此以免遗漏）：

- 证伪检查：故意损坏二进制/输入，确认 harness 非零失败（防空跑误报）
- 输出 PNG 非空与维度回读已在用例内覆盖（checkpng + -s 检查）

## 交付物

| 文件 | 说明 |
|------|------|
| bin/xbrzscale | 放大工具（arm64 ELF，OHOS 签名，0755） |
| lib/libxbrzscale.a | 可链接静态库 |
| include/libxbrzscale.h、include/xbrz/*.h | 公开头文件 |
| licenses/License.txt | GPL-3.0-only 文本 |

## 注意事项

- 产物含可执行文件，软件级 `archives/x/xbrzscale/commands.json` 已声明（R38）。
- `xbrzscale --version/--help` 同样走参数校验分支（退出码 1），CI L2 若探测此类 flag 需以“用法报错即正常”理解。
- 本机为 Windows（大小写不敏感 + CR 文件名限制），工作树以 sparse-checkout 排除上游
  `archives/g/gama` 坏文件名与 `archives/l/libXext` 大小写碰撞目录后检出；
  本 PR 仅新增 `archives/x/xbrzscale/**`，不受影响。
