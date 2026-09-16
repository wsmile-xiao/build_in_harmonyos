# distorm 3.5.2.b — 适配笔记

> 档案创建时间：2026-09-10
> 最后更新：2026-09-10
> 状态：未提交工作树（待 HMBS 真机预检：conan create + test_package + 上游测试审计确认）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | distorm（diStorm3） |
| 版本 | 3.5.2.b（上游 tag 为 3.5.2b，见下） |
| 构建系统 | Makefile（无 configure、无 CMake，手写编译命令） |
| 源码 | https://github.com/gdabah/distorm/archive/refs/tags/3.5.2b.tar.gz |
| sha256 | dabfb5915b72b4e3179a951b8d16e81a3b4f68820d83fda1484e80f2fd0412a5 |
| 依赖 | 无（纯 C，零依赖） |
| 许可证 | BSD-3-Clause |

版本说明：上游 release/tag 命名为 `3.5.2b`（无点），本任务指定配方版本为 `3.5.2.b`；
`conandata.yml` 指向 tag `3.5.2b` 的官方归档，`conanfile.py` 的 `version` 与目录名均使用任务指定的 `3.5.2.b`。

## 二、上游测试审计（R51 三步法第一步：清点）

清点方法：下载官方归档并列出全部文件，检查测试目录、测试目标与测试运行器。

1. 顶层无 `tests/`、`test/`、`check*` 目录；无 CTest/CMake/meson 测试接线。
2. `make/linux/Makefile` 仅 `all/clean/clib/install` 四个目标，无 `check`/`test` 目标；
   `examples/linux/Makefile` 仅构建演示程序 `disasm`。
3. `examples/tests/main.cpp` 为演示采样（固定 3 字节 decompose + 打印，无断言，恒返回 0），
   其余 `examples/{linux,win32,java,cs,ddk}` 均为平台演示或语言绑定示例。
4. 唯一实质测试套件是 `python/test_distorm3.py`（`findstr` 计数约 367 个 `def test_` 方法，
   11 个 TestCase：TestMode16/32/64、TestInstTable、TestAVXOperands、TestMisc、TestMisc2、
   TestPrefixes、TestInvalid、TestFeatures、TestAPI），但：
   - 测试对象是 CPython 绑定模块 `distorm3`（`import distorm3`），不是 C 库本身；
   - 约半数用例需经 yasm 汇编器在线汇编测试向量（`YASM_PATH`，默认 `yasm`）；
   - 本配方只打包 C 静态/动态库，不构建 Python 扩展；OHOS 无 yasm 预编译包，
     低成本补齐不可行，故未接入。
5. 结论：C 库侧可接入的上游测试数为 0，`test_package/MANIFEST.yml` 已按规范写入
   `upstream_tests_exist: false` + 非空 `upstream_test_audit`；`build()` 中不伪造
   `make check` 调用（上游根本不存在该目标）。

## 三、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
|（无）| 纯 C99 源码，clang 直接可编译，无需修改 | 无需修改 | 无补丁 |

## 四、配方设计要点

- 编译命令复刻上游 `make/linux/Makefile` 旗标：
  `-fPIC -O2 -Wall -DSUPPORT_64BIT_OFFSET -DDISTORM_STATIC -std=c99`，
  编译 `src/` 下 8 个 C 文件后 `ar rcs libdistorm3.a`（默认静态）或
  `cc -shared -o libdistorm3.so`（`shared=True` 时）。
- 库文件名保持上游命名 `libdistorm3`（不改名为 `distorm`），`package_info()` 的
  `cpp_info.libs = ["distorm3"]` 与头文件引用对应。
- R33：编译器/归档工具路径从 Conan conf `tools.build:compiler_executables`
  字典获取，`self.run()` 命令中无 `${CC}` 等 shell 变量引用。
- 非系统同名库（`/lib`、`/lib64` 下无 `libdistorm3.so`），保留动态库选项，不做 R26 静态强制。
- 纯库类型，无可执行产物，不需要 `commands.json`（R38）。
- test_package 采用 CMake（CMakeDeps + CMakeToolchain，与 zlib 范式一致），
  两个真实调用库 API 的测试程序（R34 合规），共 20 项断言。

## 五、编译验证命令（待 HMBS 真机预检执行）

```bash
# 真机（HarmonyOS PC，ohos-aarch64 profile）执行
conan create archives/d/distorm/3.5.2.b \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --user=ohpcd --channel=stable --build=missing
```

预期：`conan create` 成功，日志含 `Testing package`，`test_version` 与 `test_decode`
各自退出码为 0；上游 C 测试数 0（无可运行目标），Python 绑定套件约 367 用例未运行
（缺 yasm 与 CPython 扩展构建，见补充说明）。

## 六、结束记录

- **最终状态**：未提交工作树，等待 HMBS 真机全部门禁通过后统一提交推送。
- 本轮未执行 `git commit` / `git push`，未创建 PR，未调用 GitCode 写接口，未写 `.hmbs/pr.json`。
