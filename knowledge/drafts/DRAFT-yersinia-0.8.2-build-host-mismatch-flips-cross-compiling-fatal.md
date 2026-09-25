# DRAFT-yersinia-0.8.2: 为绕过老 config.guess 把 `--build` 写成 gnu，会让 autoconf 判 cross_compiling=yes，包内 AC_TRY_RUN 运行探测随即硬 fatal

## 基本信息
- **严重度**: 2
- **类别**: autotools, cross-compile, triplet, autoconf-probe
- **作者**: QC-10
- **来源 PR**: (本 PR)
- **来源 commit**: (待提交后回填)
- **适用构建系统**: autotools（configure 由 autoconf 生成；`autoreconf -fi` 路线同样适用）

## 错误特征
```
checking whether we are cross compiling... (读数为 yes 一侧)
checking for BPF device sending support... configure: error: in '/.../build-release':
configure: error: cannot run test program while cross compiling
```
关键指纹：**失败点在包自己写的一个"跑一下才知道"的探测上**（本例 `AC_TRY_RUN` 探 BPF 设备发送支持），
而不是编译器可用性检查；autoconf 给出的 `cannot run test program while cross compiling` 是
AC_TRY_RUN 在 `cross_compiling=yes` 且该探测**没有** `ac_cv_*` 缓存变量兜底时的默认 else 分支。

## 根因分析
autoconf 的 `cross_compiling` 只看 `--build` 与 `--host` 两个三元组是否相同，与"这台机器实际能不能
执行产物"无关。

鸿蒙 PC 适配的事实是：**构建机就是目标机**（aarch64 设备上跑 clang，产出的 ELF 就在本机跑）。
但仓内经验条目为了绕开 2013 年以前的 `config.guess` 不认识 `*-linux-ohos`，普遍写成

```
--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos
```

这一写法把 `cross_compiling` 从 `no` 翻成 `yes`，后果是包内所有运行型探测换分支执行：
- 有 `ac_cv_*` 兜底的 → 变成"假设值"，只是不精确；
- **没有兜底的（本例）→ 直接 as_fn_error 硬失败**，configure 走不完，连编译都进不去。

## 推荐方案
**方法**: `align-build-triplet-with-host-on-ohos-native-target`

**说明**: 两个三元组都写 OHOS，靠 `tool_requires("automake/1.18")` + `autoreconf -fi` 换掉自带的老
`config.guess`/`config.sub`（automake 1.18 自带的 config.sub 已接受 `aarch64-unknown-linux-ohos`，
仓内实测过），从而**既不需要骗 config.guess，也不翻转 cross_compiling**。

**验证/命令**（本包实测的改前/改后读数）:
```bash
# 改前：generate() 里 --build=aarch64-unknown-linux-gnu
configure: error: cannot run test program while cross compiling   # G2 FAIL，停在 configure

# 改后：--build 与 --host 同为 aarch64-unknown-linux-ohos
checking whether we are cross compiling... no
checking for BPF device sending support... <继续，不再 fatal>      # configure 通过，进入编译

# 复算口径
grep -n "cross compiling"                    archives/y/<pkg>/<ver>/reports/conan-create.log
grep -n "cannot run test program while"      archives/y/<pkg>/<ver>/reports/conan-create.log
grep -n "AC_TRY_RUN" <src>/configure.in      # 判断本包是否属于高危形态
```

## 适用边界 / 反例 / 解除条件
- **适用**: 构建与运行同机的鸿蒙 PC 适配；且 `configure.in/configure.ac` 里 grep 得到 `AC_TRY_RUN`
  （或等价"编译后执行"的探测）而该探测无缓存变量/开关兜底。
- **反例一（不适用）**: 真交叉（x86 宿主出 aarch64 产物且产物跑不了）——此时 `cross_compiling=yes`
  是事实，必须逐条预设 `ac_cv_*`，不能靠改三元组解决。
- **反例二（先决条件）**: 包自带的 `config.sub` 极老、连 `*-linux-ohos` 都不接受时，直接写
  build==host 会退回 E007（`cannot guess build type`）；须先用 automake 的新辅助件重生成
  （本例走 `autoreconf -fi`），或按 E007/E160 换 config.guess/sub。
- **反例三（无需改动）**: 包内探测全是编译期（`AC_CHECK_LIB`/`AC_CHECK_HEADERS` 等，不执行产物）时，
  写 `--build=gnu` 不会暴露本症状，本条不构成必改项。
- **解除条件**: 上游为这些探测补上缓存变量或 `--disable` 开关。

## 关键词
交叉三元组, cross_compiling, AC_TRY_RUN, 运行型探测, ac_cv 预设, --build gnu 的代价,
本机即目标机, aarch64-unknown-linux-ohos, config.sub 新旧, 判定翻转, configure fatal

---
*与相近条目的区分：**E467** 同样以 "cross compiling" 报错，但其根因是 `AutotoolsDeps` 导出 LIBS
让 autoconf **最早期**的 run 探针链接整个依赖闭包而失败（签名 `cannot run C compiled programs`），
修法在依赖导出面；本条签名是 `cannot run test program while cross compiling`（发生在包自己的中后段
探测），根因是三元组声明，修法在三元组。**E007**（`cannot guess build type`）正是本条所讨论写法的
**动因**，本条补的是该写法的代价与适用边界。**E159** 是 CMake `TRY_RUN` 在交叉模式下不支持，同族不同构建系统。*
*另与仓内经验的冲突已在 `.kv` 的 `conflicts_with` 字段写明：不否定"真交叉用 `--build=gnu`"，
但鸿蒙 PC 本机适配属反例。*
*实测来源：yersinia 0.8.2（任务 12288）。*
