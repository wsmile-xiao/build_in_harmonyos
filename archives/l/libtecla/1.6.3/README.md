# libtecla 1.6.3 — HarmonyOS PC 适配

libtecla（Tecla 命令行编辑库）提供交互式命令行编辑、历史记录、文件名补全与通配符展开（上游 https://sites.astro.caltech.edu/~mcs/tecla/，X11 许可）。

## 构建
- 纯 C 静态库（libtecla.a/libtecla_r.a + libtecla.h）；configure + Makefile 自定义构建
- 适配要点（详见 conanfile.py / notes.md）：
  - 现代 autoconf 重新生成 configure（旧版 config.status 在 OHOS 上不兼容）+ 现代 config.guess/sub + 固定 `--build/--host=aarch64-linux-ohos`
  - configure 内 umask 077→022（E046，HMDFS 拒绝 700 权限临时目录）
  - .so 链接直接 ld.lld -lc → 插入 OHOS sysroot `-L` 解决
- 产物：静态库 + libtecla.h；test_package 链接库调用 `libtecla_version()` 断言 1.6.3（PASS=3）

详见 archives/l/libtecla/1.6.3/ 的 conanfile.py、manifest.yaml、test_package/。
