# dmenu

suckless 出品的 X11 动态菜单程序（suckless/tools/dmenu），HarmonyOS PC 适配归档。

- 上游：https://tools.suckless.org/dmenu/（源码 https://dl.suckless.org/tools/dmenu-5.4.tar.gz）
- 许可证：MIT
- 构建：裸 Makefile（无 configure）
- 产物：`dmenu`（主程序）、`dmenu_run`/`dmenu_path`（配套脚本）、`stest`（文件谓词过滤器工具）
- 依赖：libx11 / libxft（含 fontconfig/freetype/libxrender/xorgproto 传递依赖）；Xinerama
  特性禁用（libxinerama 配方钉 libx11/6.4.0，与 libxft 钉的 libx11/1.8.13 同图冲突）
- 上游测试：无（N_static=0，无 check/test 目标；stest 是伴生工具非测试套件），消费者测试以
  `dmenu -v` 版本断言 + `stest -f/-d` 谓词行为断言补位（见各版本 test_package/test.sh）

## 适配要点

裸 Makefile 把 `CC=cc`、`X11INC=/usr/X11R6/include`、`FREETYPEINC=/usr/include/freetype2`
烧死，OHOS 交叉环境全部不可得；配方以 make 命令行变量覆盖（`CC`/`INCS`/`LIBS`/`PREFIX`/
`MANPREFIX`）注入 Conan 依赖路径，零补丁完成适配。细节见 `5.4/notes.md`。
