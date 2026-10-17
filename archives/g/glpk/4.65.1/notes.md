# glpk 4.65.1 编译笔记（HarmonyOS PC · Conan autotools + oldapi/lpx 兼容层）

## 定位
- 4.65.1 = 4.65 官方源码 + 官方 oldapi/lpx 兼容层，独立编译单元 `liblpx.a` 编入制品。
- 动因：osi 0.108.11 的 OsiGlpk 使用 189 处 lpx_* 旧 API；GLPK >= 4.53 官方源码已移除
  lpx_*，仅 examples/oldapi 官方兼容层（4.48 定义）能提供。R05 已实测 liblpx.a
  （111 个 lpx_* 符号）链接后 OsiGlpk 段编译并全量运行通过（1501 PASSED / exit 0）。
- 发布带 lpx_* 兼容符号的 glpk/4.65.1 制品，使 COIN-OR 系求解器接口可实例化该段。
  （依赖 osi 侧 DRAFT-osi-0.108.11-glpk5-lpx-api-removal 知识条目，本 PR 为其制品侧落地。）

## 关键适配（相对 4.65）
1. **兼容层来源**：与 4.65 同一官方 glpk-4.65.tar.gz（sha256
   4281e29b628864dfe48d393a7bedd781e5b475387c20d8b0158f329994721a10）内
   examples/oldapi/lpx.c + lpx.h；lpx.c sha256 a15f95d6…，lpx.h sha256 5fe3a003…。
   禁止任何非官方来源/缓存路径/代理改写地址。
2. **独立编译单元**：build() 在 autotools 构建 libglpk 后，用 Conan toolchain
   （tools.build:compiler_executables 的 c + CFLAGS）将 lpx.c 编译为 lpx.o，
   `ar rcs` 打包为 liblpx.a（-fPIC，与共享 libglpk 兼容）。lpx.c 只依赖
   glpk.h + lpx.h，无 gmp 头依赖，符号解析在消费者侧最终链接完成。
3. **安装导出**：package() 把 liblpx.a 装入 lib/、lpx.h 装入 include/；
   package_info 导出 cpp_info.libs = ['glpk', 'lpx']，消费者 `-lglpk -llpx` 即得
   lpx_* 全部旧 API 符号。
4. **消费者用例**（R34 + 消费者硬门禁）：test_package/test.c 只经公开
   lpx.h/glpk.h 头与公开链接目标，用 lpx_* 旧 API 真解官方例题 LP，校验
   最优值 z=733.333333、LPX_OPT 状态与 lpx_check_kkt（LPX_K_KKTPDE）KKT 误差≈0。

## 版本与分支
- 版本 4.65.1（R37：制品仓不支持同版本多 revision，新增兼容层必须升适配后缀版本号）。
- 分支 fix/glpk-4.65.1（branch_transition_authorized: true，由 feat/glpk-4.65 过渡）。
- 与 ohpcd 既有 glpk/4.65、glpk/5.0 并存，不 delete/replace 他人制品。

## 验证（任务首轮由本任务执行并回报）
- 制品验证（发布前）：glpk.h 含 lpx.h 声明的 lpx_* 函数集；`nm` liblpx.a 含
  lpx_* 符号（不少于 R05 的 111 个）；与官方 oldapi lpx.h 对照集合差为 0。
- conan create（W3）→ conan upload 到 ohpcd → conan list/download 复验可消费。
---

**编译结束**: 2026-09-19 03:06
**最终状态**: built
