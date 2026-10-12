# routino 3.4.3 适配笔记

## 编译环境
- 构建系统: makefile（上游自定义 Makefile.conf + src/Makefile，无 configure/CMake）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（Conan conf tools.build:compiler_executables）
- 状态: built（待真机预检验证）

## 编译步骤

只构建并打包 `src/`（库 + 工具）与 `xml/`（路由数据文件）：
`doc/` 为空目标，`web/` 是演示站点（需额外下载），`extras/` 安装目标为空，
`python/` 绑定需 swig（上游 Makefile 仅在 HAVE_SWIG 且 HAVE_PYTHON 时构建）。

```bash
make CC=$CC LD=$CC AR=$AR RANLIB=$RANLIB SHELL=$CONFIG_SHELL \
  CFLAGS="<上游基线> -I<zlib,bzip2 include>" \
  LDFLAGS="-L<zlib,bzip2 lib> -lm -pthread -lpthread -lbz2 -lz" \
  FASTMATHS=0 -j1 -C src <tools...> libroutino.so.0.0.0 libroutino-slim.so.0.0.0
# 构建树内用实文件拷贝代替 ln -sf soname 链接（HMDFS 无 symlink，仅供测试）
# router+lib / router+lib-slim（链接 .so 拷贝）
make -C src/test is-fast-math
make -C src/xml test-skeleton
make -C xml all   # perl 生成 tagging-drive/ride/walk.xml
# shared=False 时再用 $AR 生成 libroutino.a / libroutino-slim.a
```

打包不调用 `make install`（install-local 依赖 all-local，其 `ln -sf`
soname 步骤在 HMDFS 上必然失败），改用配方内显式 `copy()` 清单：
7 个直连工具 → `bin/`，`routino.h` → `include/`，
`libroutino.a` / `libroutino-slim.a` → `lib/`，
6 个路由数据 xml → `share/routino/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ln -sf` 创建 .so soname 链接 | HMDFS 不支持 symlink（libfreenect 经验、bzip2 先例） | `validate()` 在 OHOS 下拒绝 shared=True，只出静态包；测试所需的 .so 用构建树内实文件拷贝代替 |
| 2 | 上游默认 `-ffast-math` 导致路由比对轻微漂移 | Makefile.conf 注释明示 "makes test cases fail slightly" | 全程 `FASTMATHS=0`（追加 `-fno-fast-math`），测试严格比对 |
| 3 | 测试脚本 shebang `#!/bin/sh` 在 OHOS 上不存在 | R5：OHOS 无 /bin/sh | 全部测试子进程经 `$CONFIG_SHELL`（hnp bash）显式调用 |
| 4 | `Routino_CheckAPIVersion()` 返回值误断言 | 该宏返回 `ROUTINO_ERROR_NONE`(0) 而非版本号（见 routino.c） | test 用例断言 `rc == ROUTINO_ERROR_NONE` |
| 5 | rule4 禁止对 stdout 做字符串计数 | catch2 事故教训 | 126 个上游用例全部按子进程退出码计数，结果写入 upstream_tests.log 备查 |
| 6 | `printenv: Argument list too long` 刷屏后 Signal 9 | `generate()` 内 `VirtualBuildEnv` 后又 `save_script("conanbuild")`，同名聚合递归 source（qqwing 先例），环境膨胀超 ARG_MAX | 改用自定义名 `routino_cc_env`，`build()` 内 `env=["conanbuild","routino_cc_env"]`（zita 先例） |
| 7 | preflight `make: /data/service/hnp/bin/clang: No such file or directory` | profile 硬编码编译器/shell 绝对路径在真机上过期（工具实际在 HMBS PATH 的 `/storage/.../usr/local/bin`，SHELL=/bin/sh） | `generate()` 经存在性检查解析 CC/CXX/AR/RANLIB（ical2html 先例：conf 绝对路径仅在可执行时采用，否则 PATH 回退到 clang/cc 裸名）；`_config_shell`/test `_shell()` 同理回退到现存 shell |

## 源码修改

无补丁（`patches/` 为空）。全部适配逻辑在配方内：
编译器/链接器经 `generate()` 写入 routino_cc_env 环境（R33，指南 4.3），
依赖头文件/库路径经 make 命令行 `CFLAGS`/`LDFLAGS` 注入，
平台判断用 `in ("Linux", "OHOS")`（R32）。

## 依赖版本

- zlib/1.3.1（gzip 支持，上游 INSTALL.txt 必需）
- bzip2/1.0.8（bzip2 支持，上游 INSTALL.txt 必需）
- 构建时工具：perl（xml 数据生成与 waypoints.pl）、diff

## 验证结果

上游套件（126 个，退出码口径）：
15 OSM × 6 配置（normal/lib/pruned × non-slim/slim）= 90，
fat-vs-slim diff 比对 3 个，
XML 解析检查 33 个（good 1 个必须通过 + bad 32 个必须拒绝）。
python/ 绑定测试由上游 Makefile 以 HAVE_SWIG 门控，未计入。

新增测试（3 个，test_routino 二进制自计数并打印
`HMBS_TEST_PACKAGE_RESULT`）：
CheckAPIVersion 返回码、LoadDatabase 不存在路径返回 NULL 且
`Routino_errno == ROUTINO_ERROR_NO_DATABASE_FILES`、常量断言。

```bash
# 真机预检（HMBS 后台执行）：
# conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 通过率以预检日志中的 HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT 为准
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/router*`、`bin/planetsplitter*`、`bin/filedumper*` | 路由/切图/转储工具（7 个，见 commands.json） |
| `lib/libroutino.a`、`lib/libroutino-slim.a` | 静态库（slim 版低内存） |
| `include/routino.h` | 库 API 头文件 |
| `share/routino/*.xml` | profiles/translations/tagging 路由数据 |

## 注意事项

- OHOS 包为静态（shared=True 被 `validate()` 拒绝）；`router+lib*`
  因运行时需要 `.so` 未打包，仅用于构建树内 lib 型测试。
- `ROUTINO_DATADIR` 缺省指向的 share 数据随包发布在
  `share/routino/`。
- 证伪说明：跑测试前断言全部 `*.osm` / `expected/*.txt` /
  xml 语料非空（空夹具的 diff 恒通过），严格 diff 模式
 （FASTMATHS=0）下通过即真实通过。
