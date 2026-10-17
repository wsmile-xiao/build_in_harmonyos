# readline 8.3 Conan 配方适配笔记

- **日期**: 2026-08-07
- **上游版本**: 8.3 (2024-12-13)
- **构建系统**: autotools

## 适配要点

1. **系统同名库 (R26)**：readline 是系统同名库，必须静态编译（`--enable-static --disable-shared`），避免 .so 污染 `/lib`/`/lib64`
2. **config.guess 补丁**：需添加 HarmonyOS 检测分支（`aarch64-unknown-linux-ohos`）。config.sub 已原生支持 `linux-ohos*`，无需额外补丁
3. **ncurses 依赖**：通过 `--with-curses` + `bash_cv_termcap_lib=libncursesw` 链接系统 ncurses 宽字符版本，而非 libncurses
4. **CFLAGS**：`-fPIC -O2` 必须设置，否则静态库无法链入下游共享库

## 历史记录（2026-06-05 旧格式编译）

旧格式归档已完成功能验证，结果如下：

- **编译命令**：`CFLAGS="-fPIC -O2" ./configure --prefix=$HOME/usr/local --with-curses`
- **测试结果**：17/17 全部通过 ✅
- **产物**：`libreadline.a`, `libreadline.so.8.3`, `libhistory.a`, `libhistory.so.8.3`
- **已知问题**：
  1. config.guess 无法识别 HarmonyOS → 补丁修复
  2. config.status 在 HMDFS 上临时目录创建失败 → 改用绝对路径 `$HOME/tmp/confXXXXXX`
- **预编译包**：`readline-8.3-ohos-aarch64.tar.gz` (2.78MB)

本次在此基础上创建了标准 Conan 配方（conanfile.py + conandata.yml + test_package/）。

## 待验证

- [ ] 鸿蒙 PC 上 `conan create` 编译验证
- [ ] test_package 测试通过
- [ ] 上游 `make check` 测试通过率
