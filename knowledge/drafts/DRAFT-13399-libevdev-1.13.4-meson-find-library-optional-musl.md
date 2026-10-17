# musl 无独立 librt:meson cc.find_library 需 required:false(libevdev 1.13.4 载体)

- **草稿 ID**: DRAFT-13399-libevdev-1.13.4-meson-find-library-optional-musl
- **来源**: libevdev/1.13.4 适配(积分赛依赖任务,PR 同分支提交)
- **分类**: meson / musl / portability / find_library
- **状态**: 随 PR #13399 提交(待 CI/审核)

## 问题 / 错误签名

- 上游 `meson.build` 依赖段:`dep_lm = cc.find_library('m')`、`dep_rt = cc.find_library('rt')`。
- OHOS PC(musl libc)下 `meson setup` 直接失败:`ERROR: C library 'rt' not found`(find_library 默认 `required: true`,找不到即中止)。

## 根因

1. glibc 把实时函数放在独立 `librt.so`,而 **musl 全部并入 libc.so**——musl 系统上不存在独立的 `librt`/`libm` 链接单元(仅部分发行版提供空壳兼容包)。
2. meson 的 `cc.find_library()` 语义与 `dependency()` 不同:找不到**不是**软失败,直接报错终止 setup;很多上游把它当作"总能在 glibc 上找到"的无条件调用。
3. libevdev 库本体并不引用 librt 专有符号:`clock_gettime` 只出现在测试代码,且 musl 与 glibc ≥ 2.17 都由 libc 直接提供——查找失败只是"无害的缺席"。

## 最小修复方案

1. 上游补丁(1 行 × 2):`cc.find_library('m', required: false)`、`cc.find_library('rt', required: false)`;
2. `conandata.yml` 声明补丁,`apply_conandata_patches` 应用;
3. 配方 `package_info.system_libs` 保留 `["m", "rt"]`(与仓库已发布的 libevdev 1.13.7 配方一致;OHOS 工具链对缺席的 `-lrt` 容忍)。

## 实际验证结果

- 补丁对 Debian `1.13.4+dfsg.orig.tar.xz` 解包树 `git apply --check` 通过;
- sha256 为下载原包实测;meson/头文件 musl 兼容静态检查 8/8 通过;
- 实际交叉构建由 CI `conan create` 完成(本条目随 PR 提交时 CI 待跑,结果见 PR)。

## 适用范围

- musl(OHOS PC)上以 meson 构建且依赖段含 `cc.find_library('rt'|'m'|'dl'|'pthread')` 的包;
- 同族问题:`dl`/`pthread` 在 musl 同样并入 libc,同法处理。

## 非适用边界

- 找到的库真的会被用到且 musl 无等价实现时(如某些专有实时扩展),required:false 会把链接错误推迟到链接期——此时应改实现而非吞掉查找;
- CMake 的 `find_library` 语义不同(找不到只设 NOT-FOUND 变量),不适用本条。

## 查重差异

- 仓库已有 musl-compat 系列.md 记录 libc 缺口清单,本条以 libevdev/1.13.4 为载体补充 **meson find_library 的 required 语义**这一具体触发形式与 1 行补丁修法;与 1.13.7(无补丁构建成功)的差异在于任务指定版本与显式化处理。

## 关联交付

- 本草稿与 `archives/l/libevdev/1.13.4/**` 属同一交付范围(同 PR 关联,知识库扩展路径 B)。
