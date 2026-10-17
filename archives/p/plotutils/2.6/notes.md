# plotutils 2.6 适配笔记

## 编译环境
- 构建系统: autotools (libtool 1.5.22, autoconf 2.61)
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 平台: HarmonyOS PC aarch64 (OHOS)
- 状态: adapted（--without-x 模式，OHOS 验证全绿）

## 编译步骤
1. 下载源码 plotutils-2.6.tar.gz 并解压
2. 应用 4 个补丁（0001-0004）
3. `./configure --prefix=/ --without-x --enable-libplotter=no --enable-libxmi`
4. `make -j1`
5. `make install DESTDIR=<staging>`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 HarmonyOS | E007: 版本过旧 | 补丁 0001/0002 |
| 2 | config.status Permission denied | E011: HMDFS umask 077 | 补丁 0003 (mktemp+umask077→mkdir) |
| 3 | X11 依赖缺失（libXaw/libXmu） | 仓库未适配 | --without-x 跳过 |
| 4 | z_write.c 编译失败：`incomplete definition of type 'struct png_struct_def'` | libpng 1.6 起不透明 png_struct | 补丁 0004: png_ptr->jmpbuf → png_jmpbuf() |
| 5 | gram.cc: `ISO C++17 does not allow 'register'` | 上古 bison 骨架含 register 关键字 | generate() 中 cppstd≥17 时降为 -std=gnu++14 |
| 6 | 链接失败 `-lxmi` 找不到 | 未传 --enable-libxmi | configure 增加 --enable-libxmi |
| 7 | TypeError: expected str not NoneType | 传递依赖 zlib 无 binary，package_folder=None | 遍历 dependencies 时跳过 None |
| 8 | test_probe 运行失败：无法打开流 | OHOS /tmp 只读文件系统，tmpfile() 返回 NULL | 改用 cwd 具名文件 |

## 依赖
- 必需: libpng/1.6.58.2 (PNG 输出)
- 间接: zlib/1.3.2 (通过 libpng)
- 可选（本次禁用）: libX11, libXaw, libXmu, libXext (X11 交互输出)

## 产物
- 库: libplot.a (主库，内嵌 libxmi 实现), libxmi.a (独立，需 --enable-libxmi)
- CLI 工具(7): graph, plot, spline, ode, tek2plot, plotfont, pic2plot
- 演示程序(2): double, hersheydemo

## 注意事项
- commands.json 已创建 (R38)
- R40: 图形渲染库已验证实际 PNG 输出（8 字节签名校验）
- CLI 工具冒烟测试通过：graph/plotfont/spline 链路均生成合法 PNG
- spline 是数据插值过滤器（-T=tension），非输出格式选择，正确用法: `数据 | spline | graph -T png`
- plotfont 必须指定 FONT 参数，否则报错（字体不存在时回退 HersheySerif）
