# DRAFT: 生成器工具类三方库的真实交付形态（glad 2.0.8 实证）

## 问题描述

glad 2.0.x 官方仓库是 **Python 生成器工具**（glad2）：顶层仅 pyproject.toml + `glad/` Python 包 + console_script `glad`，没有顶层 CMakeLists/Makefile、没有 C 库本体；132 个 `.c` 文件全部是 Jinja 生成模板（16 个）与消费型 test/c（105 个）和 example/c（11 个）。

若在 R47 语言预检按"任务标记 cpp vs 实测 python → env_unsupported"直接终态，将丢失该库的真实可交付形态。

## 根因

- 三方库的"官方仓库"并不总是"库本体"——可能是生成器工具
- 语言统计口径把 Jinja 模板（`.c` 后缀）和消费型测试/示例误算为库主体
- 生成器工具 + C 产出的组合形态，在"语言预检即终态"的流程里没有中间出口

## 解决方案

先评估生成器产物的 C 交付形态，再判路径：

1. **生成器离线产出 C loader**：glad 内置 Khronos XML specs（`glad/files/*.xml`），`--reproducible` 不联网拉最新 spec（日志 `intercepted attempt to retrieve resource` 证明本地文件兜底远端 URL），离线可复现：
   ```bash
   python3 -m glad --api=gl:core=4.6 --out-path=<gen> --reproducible c
   # 产出 include/glad/gl.h + include/KHR/khrplatform.h + src/gl.c
   ```
2. **conan 配方**：conandata.yml 只声明官方 HTTPS 源（R39）；build() 调生成器后由 CMake 编译 `gl.c → libglad.a` 并 install 头文件（R26 静态）。
3. **test_package**：stub get-proc-address 驱动 `gladLoadGL` 真实执行 loader 表初始化（见配对草稿：无 GPU 上下文 CI 测试函数指针表 loader）。

## 验证

- conan-verify G1/G0/G2/G3/G4 + L2/L4/L5 全 PASS
- W3 本地 CI（build_and_test.sh）1/1 Success，L0/L1/L4/L5 pass
- 上游 C 测试全量尝试：parse 4/4 + compile 76/76（生成→clang 编译）rc=0
- test_package 运行 rc=0：`loader init executed, version=4.6, table populated`

## 适用范围

- glad（2.0.x）及任何"官方仓库为生成器工具、产 C 头/源码"的库（GLEW 类、EGL loader 生成类）
- 语言预检（R47）遇到 Python/其他语言生成器 + C 产出组合时，先评估 C 交付形态再终态

## 反例 / 边界

- 若生成器产物不是 C（如 Rust 生成器），且无 cargo 工具链，才可判语言阻塞（R47 能力矩阵 Rust ❌）
- 若官方 release 已含预生成产物，直接打包产物更简，无需构建期生成

## 查重（四范围）

- 正式知识（E###/index.tsv）：零命中（glad/GL loader/生成器交付形态均无条目）
- 知识图谱（graph/）：零命中
- 草稿（drafts/）：零命中
- doc/：零命中

**路径判断**：path B（new_draft）——候选已验证、可跨库复用、查重未命中。
关系：`prerequisite_of` → 函数指针表 loader 的无 GPU 测试方法（配对草稿）。

---

**草稿状态**: 待主编审核后提升为正式条目
**最后更新**: 2026-09-10
