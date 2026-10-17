# E543 — autotools AC_CHECK_DECLS(__builtin_ffs) 在 clang 下报 builtin must be directly called

## 错误特征
```
configure: error: No ffs implementation found
checking whether ffs is declared... no
checking whether __builtin_ffs is declared... no
conftest.c:64:10: error: builtin functions must be directly called
  (void) __builtin_ffs;
```
上游日志：isl 0.28 configure（2026-09-16，task isl-0.28-r01-pc4-20），`--with-int=imath` 配置下三路 ffs 探测（ffs / __builtin_ffs / _BitScanForward）全部失败。

## 触发条件
- 构建系统: autotools（AC_CHECK_DECLS(__builtin_ffs)）
- 阶段: configuration（configure 运行期声明探测）
- 平台: HarmonyOS PC（aarch64-unknown-linux-ohos），clang 15

## 根因分析
1. OHOS musl libc 头文件（strings.h）未声明 `ffs`，`HAVE_DECL_FFS=0`。
2. configure 对 `__builtin_ffs` 的 AC_CHECK_DECLS 生成 `(void) __builtin_ffs;`（取地址写法），clang 拒绝内建函数取地址，报 "builtin functions must be directly called"。
3. `_BitScanForward` 为 Windows 专有，不可用。三路全失败 → `as_fn_error: No ffs implementation found`。
4. 实际 clang 完全支持 `__builtin_ffs`（单独编译验证通过），仅 autoconf 探测写法不兼容。

## 解决方案

### 推荐方案：configure 内预设缓存变量（preset-cache-var）
在 configure 的 `__builtin_ffs` 探测行前注入 `ac_cv_have_decl___builtin_ffs=yes`，使 ac_fn_check_decl 命中缓存，跳过编译探测：
```bash
perl -0pi -e 's/(ac_fn_check_decl "\$LINENO" "__builtin_ffs")/ac_cv_have_decl___builtin_ffs=yes\n$1/' configure
```
isl_config_post.h 已有 `#if (HAVE_DECL_FFS==0) && (HAVE_DECL___BUILTIN_FFS==1) #define ffs __builtin_ffs` 分支，只需 HAVE_DECL___BUILTIN_FFS=1 即自动映射。

### 备选方案：改写 configure.ac 用直接调用探测
用 `AC_LINK_IFELSE([AC_LANG_PROGRAM([], [return __builtin_ffs(1) != 1;])], ...)` 替代 AC_CHECK_DECLS，调用而非取地址。

### 禁止做法
- ❌ 不禁止任何具体做法，但注意：不要改系统头文件，不要用 `#define ffs` 硬编码（需受 HAVE_DECL_ 宏保护）。

## 验证
```bash
cd $BUILD_SRC_DIR && grep -c ac_cv_have_decl___builtin_ffs configure   # 1
./configure --prefix=$DEFAULT_PREFIX --with-int=imath && make -j4      # exit 0
make check                                                             # 16/16 PASS
```

## 关联条目
- 相关: E129（HMDFS umask 权限）、E007（config.guess/sub 平台识别）
- 来源: isl 0.28 适配（isl-0.28-r01-pc4-20，2026-09-16）
