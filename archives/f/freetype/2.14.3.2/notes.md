# freetype 2.14.3.2 适配笔记（R37 递增：2.14.3 / 2.14.3.1 已发布制品仓）

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-25
- 编译器: clang 15（/data/service/hnp/bin，OHOS SDK）
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（conan create -pr ohos-aarch64 通过，CONAN_CREATE_EXIT=0）

## 本版变化（相对 2.14.3.1）
1. **test_package R34 实质测试**：test.c 由 dlopen 空壳改为真实调用
   FT_Init_FreeType → FT_Library_Version → FT_New_Face → FT_Get_Char_Index('A')
   → FT_Load_Glyph → FT_Done_Face → FT_Done_FreeType，并真实链接 `-lfreetype`
   （L1e 破坏性校验：lib/ 移走则编译/运行必然失败）。
2. **test_package 编译器获取修复（E307/E529）**：原 `os.environ.get("CC")` 与
   `self.conf.get("tools.build:compiler_executables:c")` 均不可靠——OHOS conan
   2.29.1 只注册父级 key，子 key `:c` 直接 get 抛 "does not exist in configuration list"；
   `in self.conf` 又因 Conf 不可迭代崩溃。改为
   `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c")`
   回退 `os.environ.get("CC","clang")`。
3. **补丁清单收敛为 3 个官方补丁**（0001 configure TMPDIR=E011 / 0002 config.guess=E007 /
   0003 config.sub=E007），conandata.yml 声明与实际 patches/ 一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package: [conf] 'tools.build:compiler_executables:c' does not exist | OHOS conan 2.29.1 只注册父级 conf key | 读父级字典 check_type=dict 再取 "c" |
| 2 | test_package: argument of type 'Conf' is not iterable | `in self.conf` 非法 | 改为 `.get(..., default={}, check_type=dict)` |
| 3 | host configure: cannot guess build type | 本机 uname -s=HarmonyOS，config.guess 不识别 | patch 0002/0003（E007） |
| 4 | host configure: can't create ./conf*/subs1.awk: Permission denied | HMDFS umask 077 目录不可写 | patch 0001（E011，TMPDIR+umask 022） |

## 上游测试（R51 三步法实测，2026-09-25 真机 OHOS aarch64）
- autotools `make check`：官方无验证套件（install.mk:86 输出 "There is no validation
  suite for this package."，exit 0）→ N=0
- meson `tests/`：注册 1 个回归测试 issue-1063（N=1），需 FREETYPE_TESTS_DATA_DIR +
  As.I.Lay.Dying.ttf 字体；字体来自 github.com/python-pillow，本环境 github 不可达
  （已验证 curl(28)/(7)/403/404），原样数据 0/1；同一测试二进制 + 系统字体
  （/system/fonts/FTAeroSans-Regular.ttf）替代 → 1/1 通过（exit 0，59..170 字符码全加载）
- 结论：上游测试逻辑在本平台验证通过，仅官方测试数据受网络环境约束缺失（有实证）。

## 依赖版本
- 无 conan 依赖（仅系统库；--with-zlib/bzip2/png/harfbuzz/brotli=no 零外部依赖叶子）

## 验证结果
- conan create（ohos-aarch64）全绿；test_package 真机运行 FT API test OK（exit 0）
---

**编译结束**: 2026-09-25 11:59
**最终状态**: built
