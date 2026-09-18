# libdumbtts 0.3.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure；Makefile 位于 src/ 下）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++
- 状态: built
- 目标平台: HarmonyOS aarch64 (armv8)

## 编译步骤

```bash
# 源码解压后结构：src/（库源码+Makefile）、conf/（语言配置）、demo/（演示程序）
cd src
clang -fPIC -o libdumbtts.o -c -Wall libdumbtts.c      # 单文件库（dic/re 均为 #include）
clang -fPIC -shared -Wl,-soname,libdumbtts.so.0 -o libdumbtts.so libdumbtts.o
mv libdumbtts.so libdumbtts.so.0.3.1                   # 上游 RELEASE=3.1

# 配方内等价命令（conanfile.py build()）
# make -C src C=<clang> PIC=-fPIC -j1   （cwd=self.source_folder）
```

上游 Makefile 的 `install` 目标支持 DESTDIR，但安装路径为 /usr/{lib,include,share}
（非 conan 布局），故配方 package() 采用手工 copy 到 lib/ include/ res/dumbtts，
并补齐 soname 符号链接链（libdumbtts.so -> libdumbtts.so.0 -> libdumbtts.so.0.3.1）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: function definition is not allowed here` | 上游使用 GNU C 嵌套函数（gcc 专有扩展），clang 15 不支持 | 将 3 个函数内的 8 个嵌套函数（roman 的 nchar/gchar、dic_compare_word 的 chrget、do_recognize_item 的 chrget/chrgot/nchar/chcom/cmwrd）提升为文件级 static，捕获变量改为显式指针参数；生成 3 个补丁 |
| 2 | 共享库无 PIC | 上游 Makefile 仅对 x86_64 启用 -fPIC，OHOS 为 armv8 | 配方 build() 显式传 `PIC=-fPIC` |
| 3 | conan create 找不到 src | basic_layout 将工作目录置于 build-release/ | 配方 build() 用 `cwd=self.source_folder` 执行 make |
| 4 | conan-verify 知识库误命中 E538/E540 | 引擎按关键词粗配到 harfbuzz/ctx 类条目 | 以实际日志为准定位，忽略无关命中 |
| 5 | W3 junk_check 失败（cloog 残留） | main 分支 full 模式整仓扫描扫到 cloog/0.21.1 历史运行时文件 | 创建任务分支并提交，使 junk_check 走 incremental 模式（git diff origin/main...HEAD） |

## 源码修改

- `patches/0001-src-libdumbtts.c.patch` — roman() 内 nchar()/gchar() 嵌套函数提升为文件级 static（新增 roman_nchar/roman_gchar，19+19 处调用点传参）
- `patches/0002-src-libdumbtts_dic.c.patch` — dic_compare_word() 内 chrget() 提升为 chrget_dic()（7 处调用点传 &wc）
- `patches/0003-src-libdumbtts_re.c.patch` — do_recognize_item() 内 5 个嵌套函数提升为 chrget_re/chrgot_re/nchar_re/chcom_re/cmwrd_re（8 处调用点传参）

## 依赖版本

零第三方依赖（仅标准 C 库：stdio/stdlib/string/ctype/wchar）。未触发任何 conan requires。

## 验证结果

```bash
# 1) 上游 demo 功能验证
cp conf/en.conf ~/.dumbtts_en.conf
LD_LIBRARY_PATH=src ./src/demo en "hello world"   # Len=12, 输出 hello world（exit 0）
LD_LIBRARY_PATH=src ./src/demo pl "zażółć gęślą jaźń"  # unicode 转换正常（exit 0）

# 2) conan-verify（G1-G4 全通过）
ohc-run.py conan-verify libdumbtts 0.3.2          # G1 完整性/G2 干净构建/G3 同名库隔离/G4 产物 → PASS

# 3) W3 本地 CI 模拟（incremental 模式）通过
ohc-run.py finish libdumbtts 0.3.2 published       # W3 阻塞门禁通过
```

上游测试用例：0（源码包无 tests/、无 make check 目标；唯一演示程序 demo/demo.c 无断言）。
自研鸿蒙专项测试：test_package/test.c 共 3 组断言（dumbtts_TTSInit 初始化、dumbtts_WCharString 宽字符转换、dumbtts_GetString 字符串转换），conan-verify G2 中实际执行通过。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | makefile 构建配方（R33 编译器取自 conf，PIC 强制，手工 package） |
| conandata.yml | 官方源 https://www.polip.com（Debian watch 同源）+ sha256 + 3 补丁声明 |
| patches/0001-0003 | GNU C 嵌套函数提升补丁 |
| test_package/ | conanfile.py + test.c（API 断言）+ CMakeLists.txt + MANIFEST.yml |
| manifest.yaml | 版本级元数据（built） |
| reports/test-report.md | 功能测试报告 |

## 注意事项

- **上游官方源**：libdumbtts 托管于 `http://www.polip.com/files/`（作者 Bohdan R. Rau 个人站，Debian watch 同样记录此源）；本项目配方使用 https 变体（同内容，sha256 一致）。Savannah 镜像（download.savannah.nongnu.org/releases/libdumbtts/）不存在此包，切勿引错。
- **运行时配置**：库在运行时按 `/usr/share/dumbtts/xx.conf → /etc/dumbtts/xx.conf → ~/.dumbtts_xx.conf` 顺序读取语言配置；包内 conf/ 数据打包到 `res/dumbtts/`，部署时需按需放置到以上路径。
- **find_project_dir 注意**：ohc-run.py 默认将 SKILL 安装目录识别为项目根，须通过 `OHC_PROJECT_DIR` 环境变量显式指向工作区仓库，否则归档写入 SKILL 目录（违规）。

---

**编译结束**: 2026-09-17 00:32
**最终状态**: built