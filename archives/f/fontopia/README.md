# fontopia

`fontopia`（GNU Fontopia）是 GNU 的控制台字体编辑器：在终端里编辑、查看与转换控制台字体，
界面由 **GnuDOS** 控制台库（`libgnudos`，ncurses TUI 工具库）构建。

- 上游发布页：https://www.gnu.org/software/fontopia/
- 源码包：`fontopia-2.0.tar.gz`
  sha256 `0daa54bb1153f6108661e619f9b5e717f6c1e2385b25fc3a5135d4f64e5b6773`
- 许可证：GPL-3.0-or-later
- 构建系统：GNU Autotools（release tarball 自带 `configure`）
- 类型：命令行/TUI 工具（`bin/fontopia`，`package_type = "application"`）
- 上游测试：无（无 `check`/`test` 目标、无 tests 目录），交付由 `test_package` 驱动真实二进制验证
- 依赖：`gnudos/2.0`（GnuDOS 控制台库）、`ncurses/6.6`

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0 | built | 首次适配 HarmonyOS PC (aarch64) |

## 适配要点

- **依赖更正**：fontopia 依赖的是 GnuDOS（`console/*.h` + `-lgnudos`），不是 ncurses 直连；
  ncurses 须显式声明，因为 gnudos 是 application 包，Conan 2 不向消费者传递 application 的依赖。
- **musl 兼容**：`fcloseall()` 为 glibc 专有，补丁改用 `fflush(NULL)`。
- **静态链接依赖**：gnudos 包内的 `libgnudos.so.2` 未过 OHOS ELF 签名校验、设备拒载，
  故用 `fontopia_LDADD` 覆写为 `libgnudos.a` + `libncursesw.a`，消费者二进制只依赖 libc。
- **HMDFS/autotools**：源码树内以 `CONFIG_SHELL=/bin/sh` 运行 configure（E386），
  并把 `configure` 里的 `umask 077` 归一为 `022`（E011）。

## 用法

```bash
fontopia --version                 # 打印版本
fontopia --help                    # 用法
fontopia <font-file>               # 打开控制台字体
fontopia -w 8 -i 16 rawfont.bin    # 按 8x16 打开裸字体文件
```
