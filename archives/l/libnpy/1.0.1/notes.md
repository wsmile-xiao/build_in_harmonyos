# libnpy 1.0.1 适配笔记

## 编译环境
- **类型**: header-only C++14（无库编译——根 `meson.build` 仅 `declare_dependency()`，无构建目标、无 install 规则）
- **构建系统**: meson（上游根工程 + 独立 `tests/` 子工程）
- **编译日期**: 2026-09-25
- **编译器**: clang 15.0.4 / clang++ 15.0.4（aarch64-unknown-linux-ohos，OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤

### 1. 源码获取（source()）
`get()` 下载 GitHub `v1.0.1` tag tarball（10842 字节，sha256 `43452a4d…ba44`），`strip_root=True` 解压。

### 2. 打包（package()）
header-only——根 `meson.build` 没有 `install_headers()`（`meson install` 产物为空），
`package()` 直接 `copy` `include/npy.hpp` → `<pkg>/include/npy.hpp`，另拷 `LICENSE` →
`licenses/LICENSE`（与 CLI11 2.7.2 的 header-only 拷贝打包同法）。

### 3. 上游测试（原生运行——SKILL Step 2，独立于 conan create）
上游测试是独立 meson 工程（根工程不含 `tests/`），按上游 README 原样运行：
```bash
export HOME="$TASK_DIR/test-home"                       # 沙箱 HOME（§3.5）
export PATH="$HOME/.local/bin:$PATH"
cd <源码>/tests
meson setup builddir          # catch2 走 subprojects/catch2.wrap 回退下载（见 E730 草稿）
meson test -C builddir -v
```
- 测试数据由 `tests/createnpy.py` 用 **numpy** 生成（设备 python 无 numpy → 沙箱 HOME
  `pip install --user meson numpy`，PyPI 实测给出 `numpy-2.5.3-cp312-cp312-ohos_aarch64.whl`
  原生 wheel；不改全局环境——见 E733 草稿）
- **实测结果（2026-09-25，`$TASK_DIR/native-test.log` 逐字留档）**：
  - meson 层：`Ok: 2` / `Fail: 0`（`test read` + `test write`，注册 2）
  - Catch2 层（test-read）：`All tests passed (87 assertions in 15 test cases)`

## 上游测试清点（R51 三步法·第一步，被审版本 v1.0.1 tarball 全量清点）

| 口径 | 计数 | 取数命令 / 依据 |
|------|------|----------------|
| 源码宏数（Catch2 `TEST_CASE`，**声明 N**） | **16** | `grep -c TEST_CASE tests/test-read.cpp` |
| 框架注册数（Catch2 实际注册） | 15 | `./test-read --list-test-names-only \| wc -l` |
| 源码断言宏（`REQUIRE*`） | 93 | `grep -c REQUIRE tests/test-read.cpp` |
| 实跑断言 | 87 | Catch2 汇总行 `87 assertions in 15 test cases` |
| meson `test()` 注册 | 2 | `tests/meson.build`：`test('test read', …)` + `test('test write', …)` |
| `test-write.cpp` | 0 case / 0 断言 | 纯 `main()` 写 6 个 `.npy` 后 `rc=0`（写入冒烟） |

**差额逐项归因**：16 − 15 = 1 case、93 − 87 = 6 断言，全部落在 `test-read.cpp:194-210` 的
上游块注释 `/* bool not supported … */`（`TEST_CASE( "Load bool data", … )` 连同其 6 条
`REQUIRE` 被上游注释掉，不参与编译）——见 E732 草稿。

**四分项（TOTAL = PASS + FAIL + SKIP + NOT_RUN = 15 + 0 + 0 + 1 = 16 = N）**：
- PASS 15（`test read` 的 15 个注册 case，Catch2 汇总全过）
- FAIL 0、SKIP 0
- NOT_RUN 1 = 块注释内 `Load bool data`（上游自注释 "bool not supported"，不可编译、无注册）
- 另：meson 第 2 个测试 `test write`（0 断言冒烟）rc=0 通过——它在任何"用例"口径下均为
  0 用例，单列于此不并入 N（避免口径混用）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan-init` 给出的是 **Autotools 模板**（`AutotoolsToolchain`/`--enable-static`） | 模板选择未读 prescan 的 meson 结论（工具缺陷，记 feedback） | 手写 header-only meson 配方覆盖模板 |
| 2 | 根 `meson.build` 无 `install_headers()`，`meson install` 产物为空 | 上游把 libnpy 设计为 subproject 消费（`declare_dependency`），不自带安装 | `package()` 直接 `copy` 头文件 |
| 3 | 上游测试数据需 **numpy**，设备 python 无 | 上游 CI 靠 `pip install numpy` | 沙箱 HOME `pip install --user numpy`（ohos_aarch64 wheel） |
| 4 | `dependency('catch2')` 系统查未命中 | conan 侧无 pkg-config 暴露 + `--wrap-mode=nodownload` 未启用 | 允许上游 wrap 回退下载（GitHub + wrapdb 实测可达，sha256 由 wrap 锁定） |
| 5 | 源码 grep 计数（16/93）> 实跑（15/87） | 上游块注释掉的 bool 用例 | 声明 N=16 源码宏口径，NOT_RUN=1 归因留档 |

## 源码修改

**无**——0 补丁（`patches_applied: []`，`conandata.yml patches: {}`）。配方适配不改上游任何文件。

## 依赖版本

| 组件 | 版本 | 用途 |
|------|------|------|
| clang / clang++ | 15.0.4 (OHOS SDK) | 编译 |
| ninja | 1.13.1 | meson 后端（设备 PATH 内置） |
| meson | 1.11.1（沙箱 pip） | 上游 tests/ 构建 |
| python3 | 3.12.9 | 测试数据生成解释器 |
| numpy | 2.5.3（沙箱 pip，ohos_aarch64 wheel） | `tests/createnpy.py` 生成 `.npy` 夹具 |
| Catch2 | 2.13.8（上游 wrap 下载，sha256 锁定） | test-read 断言框架 |

## 验证结果

```bash
# 原生上游测试（2026-09-25，沙箱 HOME）
meson test -C builddir -v
#   Ok: 2 / Fail: 0
#   All tests passed (87 assertions in 15 test cases)

# 消费者验证（conan create 的 test_package，8 项具名检查）
./test_libnpy    # 8/8 PASS
```

- **上游测试**: N=16（源码宏）→ 实跑 15、PASS 15、FAIL 0、SKIP 0、NOT_RUN 1（块注释归因）
- **断言口径（另列不混用）**: 源码 93 → 实跑 87，87/87 全 PASS
- **meson 层**: 注册 2，Ok 2 / Fail 0（2/2 = 100%）
- **消费者（鸿蒙特有）**: 8/8 PASS（见 `test_package/test.cpp`）

## 注意事项

- 零运行依赖：`requires` 为空，消费者只继承头文件路径。
- `tests/` 与根工程相互独立（`tests/meson.build` 自带 `project()`），切勿把 `subdir('tests')`
  加进根工程——上游刻意分离。
- 上游不支持 bool dtype（`npy.hpp` `dtype_map` 无 `bool`，测试已注释），消费侧读 bool 会抛
  `std::out_of_range`（`dtype_map.at`）。
