# ncurses ABI 6 默认 widec：窄字符包必须显式 `--disable-widec`

配套草稿：`knowledge/drafts/DRAFT-libncurses-6.6-narrow-abi-link-test.kv`

## 现象

1. 以为"不加 `--enable-widec` 就是窄字符构建"，但 configure 打印
   `checking if you want wide-character code... yes` 与 `ABI suffix: w`，产物仍是
   `libncursesw.a` / `ncursesw6-config`。
2. 想真正构建窄字符版本时，`make -j1 check` 在 `ncurses/Makefile` 的 `link_test`
   目标上链接失败：

   ```
   ld.lld: error: undefined symbol: init_extended_color_sp
   ld.lld: error: undefined symbol: init_extended_pair_sp
   ld.lld: error: undefined symbol: free_pair_sp
   ld.lld: error: undefined symbol: find_pair_sp
   ld.lld: error: undefined symbol: reset_color_pairs_sp
   make[1]: *** [Makefile:364: link_test] Error 1
   make: *** [Makefile:131: check] Error 2
   ```

## 根因

`configure` 在 ABI 6 下把 `cf_dft_widec` 默认设为 `yes`（`configure` 内
`cf_dft_widec=yes` for `cf_cv_abi_version=6`）。因此：

- **窄字符必须显式 `--disable-widec`**；顺带决定库名后缀、config 脚本名
  （`ncurses6-config` vs `ncursesw6-config`）和 pkg-config 模块名
  （`ncurses/form/menu/panel/ncurses++` vs `ncursesw/...w`）。
- 扩展颜色（extended colors / 256+ 色对）被 `configure` 限制在 wide 库：
  `--enable-ext-colors ... WARNING: This option applies only to wide-character library`。
  即 `NCURSES_EXT_COLORS` 在窄字符配置里恒为 0。

但 `ncurses/curses.priv.h` 的守卫漏了这一层：

```c
#define USE_EXT_SP_FUNC_SUPPORT (NCURSES_SP_FUNCS && NCURSES_EXT_FUNCS)
```

`link_test.c` 由 `ncurses/base/MKlib_gen.sh` 从 `curses.h` 生成，凡带
`/* implemented:EXT_SP_FUNC */` 的声明都会展开成 `#if USE_EXT_SP_FUNC_SUPPORT` 的调用。
`NCURSES_EXT_FUNCS=1` 时该宏为真，于是 9 个只在 `NCURSES_EXT_COLORS` 下实现的入口被引用，
而库中并不存在它们 —— 链接必然失败。

## 处置

1. 配方显式传 `--disable-widec`，并按窄字符命名同步 pkg-config / config 脚本 / 库名。
2. 给这 9 个入口单独打 tag 并补上正确的守卫，只排除"本来就没有实现"的符号：

   - `include/curses.h.in`：把
     `alloc_pair`、`extended_color_content`、`extended_pair_content`、
     `extended_slk_color`、`find_pair`、`free_pair`、`init_extended_color`、
     `init_extended_pair`、`reset_color_pairs` 的 9 条 `NCURSES_SP_NAME(...)` 声明的
     tag 从 `implemented:EXT_SP_FUNC` 改成 `implemented:EXT_COLOR_SP_FUNC`；
   - `ncurses/curses.priv.h`：新增
     `#define USE_EXT_COLOR_SP_FUNC_SUPPORT (NCURSES_SP_FUNCS && NCURSES_EXT_FUNCS && NCURSES_EXT_COLORS)`。

   `link_test` 对其余已实现入口的链接完整性覆盖保持不变。

3. **不要**用 `-Wl,--unresolved-symbols=ignore-all` / 删掉 `link_test` 依赖等办法整体
   绕过 —— 那会把真正的链接完整性检查一起关掉。

## 验证

```bash
grep -n "ABI suffix" config.log              # 窄字符应为 "ABI suffix: (none)"
ls lib/libncurses.a bin/ncurses6-config      # 窄字符产物命名
make -j1 SHELL=/bin/sh check                 # 打补丁后退出码 0
```

实测（HarmonyOS PC，aarch64-unknown-linux-ohos，clang 15.0.4）：补丁后
`make -j1 check` 通过 144 项检查（86 个 `test/programs` 入口 + 57 个头文件独立编译 +
1 个 `link_test`）。
