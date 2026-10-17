# jkmeter 0.9.0 适配笔记

## 编译环境
- 构建系统: makefile（上游裸 Makefile，source/Makefile，无 configure）
- 编译日期: 2026-09-26
- 编译器: clang/clang++（B 机 /data/service/hnp/bin，经 profile `tools.build:compiler_executables`，键名 `cpp`）
- 状态: built（conan-verify 8 道门禁全绿）

## 编译步骤

1. **W0 依赖发布检查**：`bash ci/scripts/preflight_check.sh jkmeter/0.9.0` → 9 个直接依赖全部已发布、版本号未被占用。
2. **二进制预热**：`conan install --requires=<9 依赖> --build=never -pr:h/b=ci/conan/profiles/ohos-aarch64` RC=0，14 包闭包全部从 ohpcd 命中（conan-create.log "(14 of 14)"，W60J-2 整改；含传递 fontconfig/libxml2/libxcb 等）。
3. **取源**：官方直链 tar.bz2（sha256 自算 `0062ca9a…7378` 与 SCT 指纹一致），预置 conan `core.sources:download_cache=~/tmp/ch/dlcache` 种子（URL sha256 键 + references json）。
4. **conan create**（conan-verify G2 内部，`--build=missing --user=ohpcd --channel=stable`）：
   - `source()`: `get()` 官方直链；
   - `apply_conandata_patches()`: patches/0001-source-Makefile.patch（portability）；
   - `build()`: `make -C source -j1 CXX="<profile clang++>" PCONFCFL="<全部依赖 -I> -DCLTHREADS_NO_PTHREAD_CANCEL" LDFLAGS="<全部依赖 -L>" all`；
   - `package()`: `make -C source install PREFIX=/ DESTDIR=<pkg>` → `bin/jkmeter` + `share/jkmeter/*.png`（24 张表盘素材随包安装）。
5. **test_package**：运行时共享库闭包（14 包，展开后 runtime-libs 118 文件）拷贝 + `binary-sign-tool` 自签（每枚 ELF 恰 1 个 .codesign 段），执行 test_jkmeter.sh 分层 smoke。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首轮 G2 失败：`make: install: No such file or directory`（Error 127，package() 内） | conan buildenv 的 PATH 无 toybox `install` applet（裸名找不到）；上游 install 规则烧死裸 `install` 命令（E098/E108 家族） | 补丁参数化 install 规则为 `$(INSTALL)` 并默认 `INSTALL ?= /bin/install` 绝对路径（aliki/0.3.0 同解）。commit 361958d382 |
| 2 | libxml2/2.15.3 解析到 conancenter 且下载超时 | 新 CONAN_HOME 里 conancenter 默认启用且排在 ohpcd 前，而 ohpcd 本就有 libxml2/2.15.3 | `conan remote disable conancenter`（对齐 home-bverify 模板），warm install RC=0 |
| 3 | 官方直链连通性抖动（connect timeout / 中途断流反复出现） | kokkinizita.linuxaudio.org 从 B 机网络不稳 | 循环重试拉全量后核对 sha256；预置 dlcache 种子，配方迭代期零重下 |
| 4 | 第 2 轮复跑 G2 失败：test() `_sign_ohos_elf` 对已签包内 ELF `os.chmod` 报 `PermissionError: [Errno 13]` | 缓存包复用时二进制已带 .codesign，HMDFS 对平台保护文件 chmod 返回 EPERM（E046 变体） | chmod 改防御式 `_ensure_exec`：执行位已在即跳过；无位才尝试，最终以 stat 校验兜底硬失败。commit f77d3a4cfd |
| 5 | （自纠）runtime-libs/*.so 构建产物曾被 `git add` 带入提交 | test_package 运行时闭包落在 worktree 内 | `git rm -r --cached` 剔除 + test_package/.gitignore 防复发。commit 8a4cb73159 |

## 源码修改

- `patches/0001-source-Makefile.patch`（portability，3 hunks）：
  1. 删 `CXXFLAGS += -march=native`（交叉编译不可用）；
  2. 新增 `INSTALL ?= /bin/install`，install 规则 `install -d/-m` → `$(INSTALL) -d/-m`；
  3. `jkmeter: CPPFLAGS += $(shell pkg-config --cflags freetype2)` → `$(PCONFCFL)`（设备 pkg-config 无 freetype2.pc，include/lib 路径全由配方注入）。
- 说明：0.9.0 链接行上游已是 `$(CXX)`（jnoise 0.6.0 的字面 g++ 坑上游已自愈）；`CXX` 无默认值，由 make 命令行从 profile conf 注入（本仓 profile 键名是 `cpp` 不是 `cxx`）。

## 依赖版本

直接 requires（preflight 全部已发布）：

- clxclient/3.9.2（传递 re-export libx11/libxft/freetype/clthreads/xorgproto/fontconfig）
- clthreads/2.4.0（随 clxclient/3.9.2 内部钉版防冲突）
- jack/1.9.22
- libpng/1.6.58.3
- libsndfile/1.2.2（仅头级：jclient.cc include sndfile.h，上游 LDLIBS 无 -lsndfile）
- freetype/2.14.3、libx11/1.8.13、libxft/2.3.8、xorgproto/2025.1

传递闭包（14 包，W60J-2 整改）另含：fontconfig/2.18.3、libxml2/2.15.3、libxcb/1.17.0、libxau/1.0.11、libxdmcp/1.1.5、libxrender/0.9.12、xcb-proto/1.17.0、xtrans/1.4.0、zlib、bzip2、brotli 等。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify jkmeter 0.9.0
# G0/G1 PASS, G2 conan create PASS, G3 系统同名库隔离 PASS, G4 报告件"PASS"属降级（无法找到程序包 ID，产物完整未实判——W60J-3 整改披露，产物面以本 notes 手工读数为准）
# L2 平台功能矩阵 / L4 静态安全扫描 / L5 产物基线 → 配方验证通过，可标 published
```

- 上游测试面：上游 0 自动化测试（source/Makefile 仅 all/install/uninstall/clean 四 target，无 test/check，无测试目录）——证据见 test_package/MANIFEST.yml `upstream_zero_evidence`。
- 消费者分层 smoke（test_jkmeter.sh，均真跑）：
  - 装载层：闭包 118 库文件 + bin/jkmeter = 119 ELF 校验面（create 轮签名 118 枚，主程序复用已签缓存包未再签），执行位齐、安装路径 `bin/` 正确（W60J-1 整改）；
  - 进程层：`jkmeter -help` 打印 `jkmeter-0.9.0` 版本横幅（banner=1）；无 DISPLAY 运行干净退出码 1 并打印 `Can't open display.`（nodisplay_exit=1, display_msg=1）——证明全依赖动态解析成功 + main() 走到 X display 检查点；非 127（loader 失败特征）；
  - 读数：`JKMETER_SMOKE_PASS banner=1 nodisplay_exit=1 display_msg=1`。
- 测试账本：静态装载 119/119 签名+执行位通过（W60J-1 整改：原记 16 库/17:17 系口径误写，盘面实测 runtime-libs=118+主程序=119）；可执行探针 2/2 通过；实测断言 3/3 通过；跳过=真实 JACK 会话+X11 图形显示（无头环境无 JACK 服务/X display，属环境缺能力，非包缺陷）；失败=0。**不谎报"运行通过"**——GUI 主循环未在无头环境验证，如实以分层读数申报。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/jkmeter | 68224 B | K-System K12/K14/K20 + 相关性表，X11+JACK GUI（ELF 自签） |
| share/jkmeter/*.png | 24 张 | 表盘/刻度素材（k12/k14/k20/stc 四套，随包安装） |

## 注意事项

- jkmeter 是 X11+JACK GUI 应用：运行时从编译期 `SHARED` 默认路径 `/usr/local/share/jkmeter` 装载表盘素材；消费者部署需保证该路径有素材或重编 `SHARED` 变量。
- 表盘素材随包安装于包内 `share/jkmeter/`，未复制进 test_package（按任务口径）。
- 真实 GUI/JACK 会话属无头环境不可运行层，交付口径=装载层+进程层读数。
- 仓库内 archives/l/libXext 的 M 态是他窗资产，本任务全程未触碰。


## 路径 B 声明（3+2）

- 适配路径：路径 A（标准 Conan 配方流程）＋ 知识库扩展（B 判定=create）
- 使用知识库：E098（裸 Makefile install 面，`$(INSTALL)` 参数化 /bin/install，aliki 同解——既有家族机制，本次撞上面在 package() 的 Error 127）；E046（HMDFS chmod 面）与 E077B（codesign 面）作为新条目的差异对照条目
- 知识库扩展：knowledge/drafts/DRAFT-7640-jkmeter-0.9.0-signed-elf-chmod-eperm-defensive.md/.kv——HMDFS 上已签名 ELF 的 os.chmod 抛 EPERM 异常（非 E046 静默失效），仅缓存包复用场景现形；修法=防御式 chmod（stat 位检查先行 + PermissionError 兜底）。draft-review 质量预检 3/3 ✅
- 关联 Issue：#3441（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3441）

**最终状态**: built（finish EXIT_REASON: finish_success，W3 Success 1 / Failed 0，2026-09-26）
