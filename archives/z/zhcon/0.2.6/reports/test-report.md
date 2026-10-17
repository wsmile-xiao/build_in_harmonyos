# zhcon 0.2.6 功能测试报告

## 测试摘要

| # | 测试 | 描述 | 结果 |
|---|------|------|------|
| 1 | zhcon 二进制存在 | 验证 `bin/zhcon` 已安装且可执行 | ✅ PASS |
| 2 | zhcon --version | 验证版本输出（退出码 0） | ✅ PASS |
| 3 | zhcon --help | 验证帮助信息输出（退出码 0） | ✅ PASS |
| 4 | zhcon.conf 存在 | 验证控制台配置文件已安装 | ✅ PASS |
| 5 | 输入法数据完整 | 验证 `lib/zhcon/input/*.mb` 数据文件已安装 | ✅ PASS |

## 测试环境

- 目标平台：HarmonyOS PC (aarch64, armv8)
- 编译器：clang/clang++ 15（OHOS SDK 26.0.0.18）
- 构建系统：Autotools（configure + make）
- 依赖：ncurses/6.5（宽字符版 libncursesw.a）、gettext/0.22.5（-lintl）
- 运行库：`-static-libstdc++` 静态链接 libc++，无 libc++_shared.so 运行时依赖

## 上游测试情况

zhcon 0.2.6 上游**无自带测试用例**：
- `make check` 各子目录（src/display/font/input/debian/tools/doc）均输出 "Nothing to be done for 'check'"
- configure/Makefile 无 TESTS / check_PROGRAMS 注册，无 test 目标
- 源码包完整文件清单检索无测试目录/测试脚本

按 R51 上游测试三步法清点结论：上游确无测试（清点证据见 notes.md 测试情况章节），故补充自研 test_package 断言（见下）。

## 自研测试（test_package，5 项断言）

test_package/conanfile.py 在 conan create 阶段真实执行：
1. `test -x <pkg>/bin/zhcon` — 二进制存在且可执行
2. `<bin> --version` — 退出码 0
3. `<bin> --help` — 帮助输出正常
4. `<pkg>/etc/zhcon.conf` — 配置文件存在
5. `<pkg>/lib/zhcon/input/` 下 .mb 输入法数据文件数量 > 0

## 验证命令

```bash
# conan 干净构建 + test_package（G1-G5 门禁）
python3 ohc-run.py conan-verify zhcon 0.2.6

# 上游 make check（无注册测试）
make -j1 check

# 二进制运行验证
LD_LIBRARY_PATH=<SDK libc++ 路径> ./src/zhcon --version
```

## 原始执行输出

### conan-verify（G1-G5 全 PASS）

```
G1: PASS (配方完整性)
G0: PASS (预构建风险评估)
G2: PASS (conan create 干净构建 + test_package)
G3: PASS (系统同名库隔离 R26)
G4: PASS (产物完整性)
✅ 配方验证通过: zhcon 0.2.6
```

### make check（上游无注册测试）

```
Making check in src/display ... Nothing to be done for 'check'.
Making check in src ... Nothing to be done for 'check'.
Making check in font ... Nothing to be done for 'check'.
Making check in input ... Nothing to be done for 'check'.
...
CHECK_EXIT=0
```

### zhcon --version

```
zhcon
```

（退出码 0）
