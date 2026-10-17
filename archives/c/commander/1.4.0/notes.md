# commander 1.4.0 适配笔记

## 编译环境
- 构建系统: makefile（上游仅有 test/clean 目标，无 configure/install）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS 工具链 /data/service/hnp/bin/clang）
- 状态: published

## 编译步骤

```bash
# 1. init-build 初始化归档（tarball 经官方 tag github.com/clibs/commander/archive/refs/tags/1.4.0.tar.gz 下载）
python3 scripts/ohc-run.py init-build commander 1.4.0 --url=https://github.com/clibs/commander
# sha256: cbc1d9d7f3774f09cb1b5743cf1757bb3ce846889a872965bd60bac6064a4bac

# 2. lang-preflight (R47): detected=c, task=cpp -> 兼容族通过
python3 scripts/ohc-run.py lang-preflight commander 1.4.0 --src .../commander-1.4.0.work

# 3. 本地静态库构建 + 安装到 TEST_PREFIX（上游 Makefile 无 lib/install 目标）
clang -c -fPIC -O2 -Wall -Wextra src/commander.c -o commander.o
llvm-ar rcs libcommander.a commander.o && llvm-ranlib libcommander.a
cp src/commander.h -> $TEST_PREFIX/include/ ; cp libcommander.a -> $TEST_PREFIX/lib/

# 4. 上游测试（Makefile test 目标 + 7 种参数组合全部符合上游期望）
make test CC=clang && ./test [-v|--verbose|-r foo|-o bar|--omit-short|-h|-V|错误路径]

# 5. 鸿蒙专项测试 + 消费者用例（对 $TEST_PREFIX 安装产物链接运行）
clang test_package/test_harmonyos.c -lcommander ... && ./test_harmonyos   # 11 断言全 PASS
clang test_package/test_consumer.c -lcommander ... && ./test_consumer -v -o out.txt -n 3 in1 in2  # rc=0

# 6. conan-init + conan-verify（配方验证 G1-G4, L2/L4/L5 全通过）
python3 scripts/ohc-run.py conan-init commander 1.4.0
python3 scripts/ohc-run.py conan-verify commander 1.4.0      # RC=0, status: published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时，init-build 下载失败 | 本机无法直连 GitHub | 经官方 tag 确认后由 ghfast.top 镜像完成传输，tarball sha256 与官方一致；conandata.yml 仍保留官方 HTTPS URL（R39） |
| 2 | conan-verify G2: `tools.build:compiler_executables:c` conf 键不存在 | Conan 2.29.1 中该 conf 是字典键 `tools.build:compiler_executables` | 按 libb64 已发布配方模式改用 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` |
| 3 | conan-verify G2: `src/commander.c` 不存在 | basic_layout 下 self.run() cwd 是 build 目录，非源码目录 | build() 中用 `self.source_folder`/`self.build_folder` 绝对路径 |
| 4 | conan-verify test_package: `commander.h` 未找到 | copy() 默认 keep_path=True，头文件装成 include/src/commander.h | package() 对 header 使用 keep_path=False，落到 include/commander.h |
| 5 | 上游测试 `./test -vro` 触发 exit(1) | `-vro` 展开后 `-r` 的必需参数是 `-o`（连字符开头）→ 合法致命路径 | 属上游真实行为，鸿蒙测试用例 4 改用 `-vo val` 验证组合短旗标展开 |

## 源码修改

无补丁（patches=0）。未修改任何上游源文件；conanfile.py 自行构建静态库。

## 依赖版本

无第三方运行时依赖（纯 C 库，仅依赖 libc/musl）。

## 验证结果

```bash
./test* 全部参数组合 rc 符合预期（上游 1/1 通过）
test_harmonyos: 11/11 PASS，clang 15.0.4 / OHOS 宏确认
test_consumer: rc=0，公开 API 解析真实命令行
conan-verify: 全门禁 PASS，conan create 复现成功
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 型配方：构建 libcommander.a + 运行上游 test |
| conandata.yml | 官方 tag 1.4.0 tarball + sha256 cbc1d9d7… |
| test_package/test_consumer.c | 消费者用例（上层 CLI 组件视角） |
| test_package/test_harmonyos.c | 鸿蒙专项测试（11 断言） |
| test_package/MANIFEST.yml | 上游/消费者/鸿蒙测试声明 |

## 注意事项

- commander 无 CLI 可执行产物（上游仅有 test 程序），非 CLI 库，不需要 commands.json（R38 仅限 CLI 库）。
- test_package 构建目录（build/、CMakeUserPresets.json）为临时产物，已在提交前清理。
---

**编译结束**: 2026-09-18 17:35
**最终状态**: published
