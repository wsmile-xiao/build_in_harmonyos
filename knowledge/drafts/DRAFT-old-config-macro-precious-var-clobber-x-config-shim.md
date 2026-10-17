# 老式 vendored AM_PATH_* 宏以 *-config 输出覆盖 precious 变量 → X_CONFIG 自建 shim（draft）

**Category**: platform-detect | autotools | conan · **Severity**: 3（blocking）· **Tool**: configure/make · **Phase**: configure

**规则**：老式 vendored `AM_PATH_*` 宏（1990s 代，无 `PKG_CHECK_MODULES` 短路）只认 `*-config` 脚本并无条件以其输出
覆盖 `X_CFLAGS/X_LIBS`——Conan relocatable 依赖包内 `*-config` 的打包机前缀固化即成死路。此时"导出 precious 变量"
完全无效，应以 `X_CONFIG=<自建 shim>` 作 configure 参数走 `AC_PATH_PROG` 预设覆盖（lbreakout2 2.6.5 案例）。

## 症状（三条路各自的失败面）

1. **无 SDL_CONFIG**：configure 硬失败——`checking for SDL - version >= 1.2.0... no`、
   `*** The sdl-config script installed by SDL could not be found`、`configure: error: lib SDL is needed`（rc=1）。
2. **导出 SDL_CFLAGS/SDL_LIBS**（sdl-mixer/sdl-image 手法）：一模一样地硬失败——probe1 与 probe2 日志逐字节相同。
3. **SDL_CONFIG 指向依赖包内 sdl-config**：configure"假通过"（`checking for SDL - version >= 1.2.0... yes`，rc=0），
   但 make 首错 `gui/stk.h:21:10: fatal error: 'SDL.h' file not found`——`SDL_CFLAGS` 已被覆盖为打包机死路径
   `-I<打包机>/.cache/conan2/.../include/SDL`（该路径在消费设备不存在，probe0 实测）。

## 根因（机理链，全部实物证据）

1. **前缀固化**：Conan 打包时 `*-config` 的 prefix 被烘焙进脚本输出；SDL1.2 时代无 pkg-config 模块名可回退
   （sibling run sdl-image 死路记录同源）。
2. **宏代际**：lbreakout2 `acinclude.m4` vendored 1999 年代 `AM_PATH_SDL` 无 `PKG_CHECK_MODULES` 短路：
   `configure:8781-8782` 无条件 `SDL_CFLAGS=`$SDL_CONFIG --cflags``、`SDL_LIBS=`$SDL_CONFIG --libs``；
   探测失败分支 `configure:8931-8932` 还把两变量重置为空串。→ 新式宏的 precious 变量导出路线在此无效。
3. **原生预设入口**：`AC_PATH_PROG` 遵守用户预设——`configure:8742` "Let the user override the test with a path"；
   宏实际只调 `--version/--cflags/--libs` 三种形（`configure:8781-8789`）。
4. **顺势覆盖**：注入 `SDL_CONFIG=<自建 shim>` 后，宏照常以 shim 输出覆盖 `SDL_CFLAGS/SDL_LIBS`——probe4 的
   config.status 实录 `S["SDL_CFLAGS"]="-I<真实包路径>/include/SDL ..."` 为消费侧真实路径。

## 处置（可复用方案空间）

- **rec（正路）**：build 目录自建三形齐备 shim + `SDL_CONFIG=<shim>` configure 参数注入（probe4 + CI 正路径）。
  - include/lib 路径由 `self.dependencies[...].package_folder` 解析拼出（能力注入，非硬编码）；
  - 未知形显式报错退出（上游宏演化时早暴露）；不碰依赖包缓存、不动 PATH、不导环境。
  - 配方样例：`archives/l/lbreakout2/2.6.5/conanfile.py`。
- **fallback A（仅新式宏有效）**：导出 `X_CFLAGS/X_LIBS` precious 变量。先做代际判别——读 vendored m4/configure，
  含 `PKG_CHECK_MODULES` 短路或对变量 set 状态检查者为新式（导出即最小干预首选）；老式宏 → 完全无效（probe2 实证）。
- **fallback B（退路）**：PATH 前置 wrapper（E433 手法，conan `Environment.prepend_path`，注意顺序）。上游硬编码
  调用 x-config 且无 X_CONFIG 入口时仍可用；作用域大、顺序敏感，能用预设时不选它。
- **forbid ①**：sed 直改依赖包缓存内 `*-config`——包缓存对配方只读 + PR 原子性（修正属依赖自己的 PR）；违反后
  缓存重解包即丢改动、其他消费者不受益。
- **forbid ②**：`SDL_CONFIG` 指向宿主系统 sdl-config——探测假通过（宿主前缀/宿主 ABI），错误推迟到 link/runtime
  期才爆（错 ABI / 链到宿主库）。

## 验证

**自包含复跑**（任何人新 shell；`${SDL12}` = 解析后 sdl12-compat 依赖包的 package_folder）：

```sh
wget https://downloads.sourceforge.net/project/lgames/lbreakout2/2.6/lbreakout2-2.6.5.tar.gz
echo "9104d6175553da3442dc6a5fc407a669e2f5aff3eedc5d30409eb003b7a78d6f  lbreakout2-2.6.5.tar.gz" | sha256sum -c
tar xzf lbreakout2-2.6.5.tar.gz && cd lbreakout2-2.6.5
./configure --disable-nls --disable-network --disable-sdltest \
  --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos ; echo rc=$?
# 观察点 A：无 SDL_CONFIG → SDL 探测段硬失败（checking for SDL - version... no / lib SDL is needed，rc=1）
printf '#!/bin/sh\ncase "$1" in\n  --version) echo 1.2.68 ;;\n  --cflags) echo "-I${SDL12}/include/SDL -I${SDL12}/include" ;;\n  --libs) echo "-L${SDL12}/lib -Wl,-rpath-link,${SDL12}/lib -lSDL-1.2" ;;\n  *) echo "unsupported sdl-config option: $1" >&2 ; exit 1 ;;\nesac\n' > sdl-config
chmod +x sdl-config
./configure --disable-nls --disable-network --disable-sdltest \
  --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos SDL_CONFIG=$PWD/sdl-config ; echo rc=$?
# 观察点 B：checking for sdl-config... $PWD/sdl-config 被接受、探测段 rc=0；
# config.status 的 S["SDL_CFLAGS"]/S["SDL_LIBS"] 即 shim 输出的真实路径
```

**本 run 留证**（`/storage/Users/currentUser/tmp/oh-device-porting-v2/lbreakout2-2.6.5/probe/`，`run_probe.sh`
四段同一解包基线、`SDL_CONFIG/SDL_*` 为唯一变量，`DONE.txt=PROBE_ALL_DONE`，Builder 2026-09-18 实跑）：

| 段 | 注入 | 结果 |
|---|---|---|
| probe1 | 无 SDL_CONFIG | configure 硬失败 rc=1（最小环境未注入依赖 CPPFLAGS/LDFLAGS，首个 fatal 落在 libpng 段；SDL 段失败文本由宏源码 `configure:8880-8884/8935` 保证） |
| probe2 | 导出 SDL_CFLAGS/SDL_LIBS | 与 probe1 逐字节同日志、同 rc=1 → precious 导出在老式宏下无效的实证 |
| probe3 | SDL_CONFIG=包内 sdl-config | configure rc=0 假通过 → make `gui/stk.h:21: 'SDL.h' file not found`（SDL_CFLAGS 被覆盖为打包机死路径） |
| probe4 | SDL_CONFIG=自建 shim | configure rc=0，config.status `S["SDL_CFLAGS"]` 为真实路径，make 越过 SDL.h 编译进入 gui 深层（SDL_mixer.h 在探针作用域外，配方中由 CPPFLAGS 补齐） |

CI 正路径佐证：`.ci_logs/conan_build_lbreakout2_2.6.5.log:95`（configure 命令行含 `SDL_CONFIG=…/b/sdl-config`）
与 `:241`（`checking for sdl-config... <shim>` 被接受）；权威 CI run2 PASS（ohos-aarch64）。

## 挂钩与近邻差异

- **principles**: P-ENV-001（id P014）——环境变量与构建系统语义冲突时优先构建系统原生机制；`X_CONFIG` 作
  configure 参数即 `AC_PATH_PROG` 原生预设入口（作者复核：比 PATH 前置/环境注入更贴合该原则取向）。
- **similar_to**:
  - **E433**（`*-config` wrapper 族最近邻）：差异 = 注入路线（PATH 前置 vs `AC_PATH_PROG` 预设参数）、根因面
    （脚本过滤自身 include vs 前缀固化 + 宏覆盖 precious 变量）；E433 不涉及宏代际决策。
  - **DRAFT-E572-removed-config-script-pkgconfig-migration**（config script 移除族）：症状类同但前提相反——
    脚本被上游删除 vs 脚本存在但输出死路。
  - **E064**（探针执行限制族）：不同构建系统/不同层，无覆盖。
  - **sdl-image-1.2.12-autotools-cross-ohos**（SDL1.2 autotools 交叉族）：`'SDL.h not found'` 家族失败面同源，
    本条补齐 `*-config` 探测语义层。

## 适用范围

任何 vendored `AM_PATH_*`/`AC_PATH_PROG` 探测 `*-config` 的 autotools 项目（SDL1.2 老宏族，gpgme/libpng/freetype
等同代项目）在 Conan 打包前缀漂移或交叉场景；本仓配方树同模式实践 3 处（sdl_ttf/2.0.11、smpeg2/2_0_0、
lbreakout2/2.6.5）此前零文档化。命中 `checking for sdl-config... no` 或 `*-config` 死路径输出时，先判宏代际
（有无 PKG_CHECK_MODULES/是否覆盖 precious 变量）再选路线，避免在老式宏上空转 `X_CFLAGS/X_LIBS` 导出。
