# dhex 0.69 — 适配记录

> 分支: feat/dhex-0.69
> 最后更新: 2026-09-10

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | dhex |
| 版本 | 0.69 |
| 状态 | built（待真机预检复核） |
| 构建系统 | makefile（上游手写 Makefile，无 configure） |
| 源码 URL | https://www.dettus.net/dhex/dhex_0.69.tar.gz |
| sha256 | 52730bcd1cf16bd4dae0de42531be9a4057535ec61ca38c0804eb8246ea6c41b |
| 依赖 | ncurses/6.6（上游 Makefile 以 LIBS=-lncurses 链接） |
| 包类型 | application（命令行工具，R38: 软件级 commands.json 已声明） |

sha256 交叉验证: 官方下载页 MD5 公示、上游 tar 包实测、Homebrew Formula/d/dhex.rb、
HaikuPorts app-editors/dhex/dhex-0.69.recipe 三方一致。

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 dhex_0.69.tar.gz（上游只发 tar 包，无 git 仓库）
- 全树 35 个文件，无 tests/、test/、spec/、t/ 目录，无测试源文件
- 手写 Makefile 仅定义 all/dhex/install/clean 目标与 .c.o 后缀规则，无 check/test/TESTS 目标
- todo.txt 原文含 "write a test suite which checks if searching/correlation etc. works"——上游自认无测试套件
- mkrelease.sh 仅执行 make + ./dhex -v 烟雾检查后打包，非测试套件
- 全树无 TEST()/TEST_F（gtest）、def test_（pytest）、ctest/meson 测试声明
结论: 上游 dhex 0.69 确实不存在测试套件，test_package/MANIFEST.yml 声明
`upstream_tests_exist: false` + 非空 `upstream_test_audit`；不虚构测试数字。
功能验证由 test_package 真实执行 dhex 二进制完成（-v 精确版本断言 +
-h 帮助断言 + -g 许可证断言，其中 -v/-h 为退出码 0 的非交互路径，不启动 ncurses UI；-g 经 gpl.c 的 warte() 每 24 行 fgets(stdin) 等待回车，stdin 为打开的 pipe 时会永久阻塞（CI build #44099 在 [test 3/3] dhex -g 处 4h 无输出超时），test.sh 已对全部 dhex 调用加 </dev/null 使 warte() 见 EOF 立即返回，可非交互输出完整 GPL），
详见 test_package/MANIFEST.yml。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| 0001-output-h-initcolors-prototype.patch | output.h 的 `void initcolors();` 旧式无原型声明改为与定义一致的 `void initcolors(tOutput* output);`（NixOS nixpkgs dhex 包同源修复；main.c 以 `initcolors(output)` 带参调用，新编译器下无原型声明属未定义行为） | portability |

补丁不含 `__OHOS__` 平台宏（R8: 纯 C 语言可移植修复）。

## 四、配方要点（conanfile.py）
- Makefile 项目：configure 缺失，build() 直接 `make -j1`（R9: HMDFS 下单作业）
- R33: CC 取自 `tools.build:compiler_executables:c`（clang），CFLAGS/CPPFLAGS/LDFLAGS/LIBS
  以 make 命令行覆盖方式注入，手写 Makefile 零修改（R6）
- ncurses/6.6 仅提供 libncursesw.a：在构建目录建 `libncurses.a -> libncursesw.a`
  符号链接满足上游 LIBS=-lncurses（沿用 dialog/1.3-20240307 同工具链已验证写法）
- 上游 `make install` 硬编码 DESTDIR=/usr/local 且含 strip 步骤，package() 改为手动
  复制：dhex → bin/，dhex.1 → share/man/man1/，dhexrc.5/dhex_markers.5/dhex_searchlog.5 → share/man/man5/
- package_type=application，cpp_info.libs=[]，cpp_info.bindirs=["bin"]
- R32: `self.settings.os not in ("Linux", "OHOS")` 拒绝非目标平台

## 五、验证记录
- 本机: 源码下载 + sha256 校验通过（三方交叉一致）；补丁上下文与 output.h 源码一致
- 真机: 待 HMBS 预检（conan create + test_package 3 断言 + 上游无测试审计门禁）
- 预检通过后由 HMBS 统一提交、推送并创建 PR，正文测试表以真机 evidence 为准

### 真机预检轮次
- 第 1 轮（待 HMBS 执行）: 工作树未提交，等待预检。
