# inform6 — OpenHarmony 编译档案

## 软件简介
inform6 是 Inform 6 交互式小说语言（Interactive Fiction）的编译器，将 `.inf`
游戏源文件编译为 Z-machine 故事文件（`.z5`/`.z3` 等）。本档案对应 David Griffith
维护的 Unix 一体化发行包 `inform-6.44-r7`：内含编译器 6.44（纯 C，约 21 个翻译单元）、
标准库 6.12.8（`std/`）、PunyInform 库 6.6（`punyinform/`）及演示/教程源文件。
许可证为 Artistic License 2.0。

## OHOS 适配要点
- 编译器本体为纯可移植 C（无第三方依赖），GNU make 单目标 `inform` 编译
  `src/*.c`；平台差异仅在 `src/header.h` 的宏分支（OHOS 走 LINUX 分支：
  `FN_SEP '/'` + `HAS_REALPATH`），无需源码补丁
- `make inform` 只编译编译器；上游 `all` 目标还会用**刚交叉编译出的二进制**
  在构建机上编译演示 `.z5`/`.z3`（交叉编译场景跑不动），故跳过，库数据原样安装
- 二进制以上游版本名 `inform-6.44` 构建后以包名 `inform6` 落盘，避免软链
  （R5）；上游 `fixlinks.sh` 的 5 个大小写别名（`English.h`→`english.h` 等）
  用文件副本实现
- 编译器默认库搜索路径在编译期烘焙（`Include_Directory`），指向
  `/usr/local/share/inform/std/{lib,include}`；鸿蒙上该路径不存在，消费者
  通过命令行 `+目录` 参数（如上游 PunyInform 规则 `-v3 +lib` 同款）或源内
  `+include_path` 指令指向包内 `share/inform6/std/` 即可
- 库数据全部为文本源文件：`std/lib`(20=15+5 别名)、`std/include`(19)、
  `std/demos`(9)、`std/tutor`(11)、`punyinform`(229)

## 依赖关系
- 无编译/运行依赖（仅 C 运行时）
- 被依赖: 无（独立 CLI 工具；inform6-library 为纯数据包，不依赖本包）

## 参考资料
- [DavidKinder/Inform6 (GitHub)](https://github.com/DavidKinder/Inform6)
- [IF Archive: inform6 source](https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/source/)
