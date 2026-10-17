# lib1541img 1.1 适配笔记

## 编译环境
- 构建系统: 上游 zimk(GNU make)；本仓库直接编译（custom）
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `1.1` 对应上游 git tag `v1.1`。
- 源码：`https://codeload.github.com/excess-c64/lib1541img/tar.gz/refs/tags/v1.1`
  sha256 `360976364c98d64485f8f7aa5630aa7f6f4907e9128bd293c94fbcd2471c0bef`。

## 编译步骤

上游用 `zimk` 子模块（GNU make 框架）构建，但发布 tarball **不含** `zimk/`，
故直接逐个编译 23 个 C 模块（`src/lib/1541img/*.c`）为静态库：

```sh
clang -c -O2 -std=c11 -DBUILDING_1541IMG -I <src>/include -o <build>/<m>.o <src>/src/lib/1541img/<m>.c
llvm-ar rcs <build>/lib1541img.a <objs>
```

模块列表见 `src/lib/1541img/1541img.mk` 的 `1541img_MODULES`（win32 专有的
`winfopen` 不编译）。

`package()` 安装 `include/1541img/*.h`、`lib/lib1541img.a`、`licenses/LICENSE.txt`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游构建不可用 | 依赖 `zimk` git 子模块，发布包不含 | 直接逐个编译 C 模块为静态库 |
| 2 | 新建文件系统状态非 OK | 对全零 D64 用 `CbmdosFs_fromImage` 得到的 FS 未初始化（BAM 无效） | 用 `CbmdosFs_create(CFO_DEFAULT)` 新建 FS，再布局到镜像 |
| 3 | `CbmdosFile_setName` 返回 void | 接口设计 | 不做返回值检查 |

## 源码修改

无补丁（`patches/` 为空）。

## 依赖版本

无外部依赖。

## 验证结果

```bash
ctest -R test_1541img
# -> lib1541img consumer test PASS (25 checks)
#   （D64_create/tracks -> CbmdosFs_create/status -> FileData/CbmdosFile -> append
#    -> writeD64 -> readD64 -> 校验文件名/类型/内容）
```

`conan create lib1541img/1.1` 退出码 0。

## 注意事项

- 引用头文件为 `<1541img/xxx.h>`；本体 API 以 `Class_method()` 命名。
- 非 Windows 平台无需 `BUILDING_1541IMG`/`STATIC_1541IMG` 宏（仅影响符号可见性）。
