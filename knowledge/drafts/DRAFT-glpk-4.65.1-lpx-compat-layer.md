# DRAFT-glpk-4.65.1-lpx-compat-layer — 把 GLPK 官方 oldapi/lpx 兼容层作为独立编译单元编入制品（liblpx.a + lpx.h）

- **知识 ID（草稿）**：DRAFT-glpk-4.65.1-lpx-compat-layer
- **路径**：Path B（知识库扩展）
- **来源事件**：glpk 4.65.1 适配 HarmonyOS PC——为 osi 0.108.11 OsiGlpk 的
  189 处 `lpx_*` 旧 API 调用提供制品侧兼容层
- **日期**：2026-09-18
- **关联条目**：`DRAFT-osi-0.108.11-glpk5-lpx-api-removal`（消费者侧草稿；
  本条目是其恢复路径 a) 的 conan 配方落地实现）

## 问题

GLPK >= 4.53 官方制品不含 `lpx_*` 旧 API（4.45-4.52 时代移除），COIN-OR 系
求解器接口（如 OsiGlpk 0.108.11）仍基于 189 处 `lpx_*` 调用编写，无法实例化。
唯一的官方来源是同一归档 `examples/oldapi/lpx.{h,c}`（4.48 定义的旧 API 模拟层），
但该兼容层不在主库内，须由配方以独立编译单元编入制品并导出。

## 根因

1. GLPK 破坏性版本变更：`lpx_*` 自 4.45-4.52 时代从主 API 移除，4.52+ 仅以
   `examples/oldapi/lpx.{h,c}` 独立可选兼容层提供。
2. OsiGlpk 0.108.11 未迁移到 `glp_*` 新 API。
3. 普通 GLPK 制品不带 `lpx_*` 符号，消费者无法 `-lglpk` 直接链接旧 API。
4. 兼容层 `lpx_main` 引用 `glp_main`（该函数在 glpsol CLI 主程序内，不在
   libglpk 库中）：独立静态库被可执行消费者整体拉入时，该未用入口产生
   `glp_main` 未解析重定位。

## 方案（R05 实证恢复路径 a) 的配方落地）

1. **兼容层来源**：必须是同一官方归档 `examples/oldapi/lpx.c + lpx.h`
   （禁止非官方/缓存/代理改写来源），记录 sha256（glpk-4.65 归档实测
   lpx.c `a15f95d6…`、lpx.h `5fe3a003…`）。
2. **独立编译单元**：配方 `build()` 在 autotools 构建 libglpk 后，用 Conan
   toolchain（`tools.build:compiler_executables` 的 c + CFLAGS，R33）将 lpx.c
   编译为 lpx.o，`ar rcs` 打包 liblpx.a；编译参数加 `-fPIC -ffunction-sections
   -fdata-sections`（lpx_main→glp_main 未用入口由消费者 `--gc-sections` 修剪）。
3. **安装导出**：`package()` 把 liblpx.a 装入 lib/、lpx.h 装入 include/；
   `package_info` 导出 `cpp_info.libs = ['glpk', 'lpx']`，消费者
   `-lglpk -llpx` 即得全部 `lpx_*` 旧 API 符号。
4. **消费者用例**（R34）：test_package 只经公开 lpx.h/glpk.h 头与公开链接
   目标，调用 `lpx_create_prob`/`lpx_load_matrix`/`lpx_simplex`/
   `lpx_check_kkt` 等真解 LP，校验 `LPX_E_OK`（200，官方 oldapi 成功返回
   语义非 0）/`LPX_OPT`/最优值/KKT≈0。
5. **制品验证**：`nm` liblpx.a 的 `lpx_*` 符号集与 lpx.h 声明集合差双向为 0；
   版本号按 R37 升适配后缀（如 glpk/4.65.1），避免覆盖既有发布版本。

## 验证

glpk/4.65.1（os=OHOS armv8）：conan create 通过；`nm liblpx.a` = 111 个
`lpx_*` 符号（与 R05 osi 侧实测一致）；与官方 lpx.h 111 个函数声明集合差
双向 0；test_package 6/6 断言 PASS（LPX_E_OK、LPX_OPT、z=733.333333、KKT≈0）；
conan-verify G0-G4+L2/L4/L5 PASS；W3 本地 CI（setup+build_and_test）通过；
W4 审计 verdict=pass。osi 0.108.11 OsiGlpk 侧 R05 已实证链接 liblpx.a 后
1501 PASSED / exit 0。

## 适用边界 / 反例

- 适用：官方归档自带 examples/oldapi 的 GLPK 4.x 系（4.53+），以及任何依赖
  `lpx_*` 旧 API 的 COIN-OR 系求解器接口消费者。
- 反例：非官方/改造兼容层来源不适用；纯 `glp_*` 新 API 消费者不需要兼容层；
  版本号不按 R37 升后缀会与既有发布冲突。

## 与既有条目关系

- similar_to: `DRAFT-osi-0.108.11-glpk5-lpx-api-removal`（同一 GLPK lpx_* 移除
  议题的制品侧 vs 消费者侧）
- caused_by: `DRAFT-osi-0.108.11-glpk5-lpx-api-removal`（osi 侧实证驱动本制品发布）
- prerequisite_of: `DRAFT-osi-0.108.11-glpk5-lpx-api-removal`（本制品发布后，
  osi 可 `--with-glpk` 实例化 OsiGlpk）
- conflicts_with: 无
