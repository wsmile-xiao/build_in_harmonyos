# DRAFT-json_dto-0.3.4-dev-subdir-build-tree-flatten

> Contributor: pc3-18 | Status: Draft | Updated: 2026-09-22
> Source: json_dto 0.3.4 HarmonyOS PC 适配（ohpc task json_dto-0.3.4-r01）
> 主题：Stiffstream 系仓库官方 tag tarball 的 CMake 构建树位于顶层 `dev/` 子目录，
> conan `source()` 仅 `strip_root=True` 后 CMakeLists.txt 不在源码根，G2 conan create 直接失败

## 现象

对 json_dto 0.3.4（https://github.com/Stiffstream/json_dto）执行
`conan create`（G2 干净构建）时报：

```text
CMake Error: The source directory ".../b" does not appear to contain CMakeLists.txt.
ERROR: json_dto/0.3.4@ohpcd/stable: Error in build() method
    cmake.configure()
```

`conan-verify` 报告 G2 FAIL，知识引擎按日志误判命中 E540/E298 类「runner 路径」或
CTest 环境条目，均不是真正根因。

## 根因

Stiffstream 系仓库（json_dto 0.3.4；同类还有 RESTinio 等）把实际工程源码放在仓库根的
`dev/` 子目录中（`dev/CMakeLists.txt`、`dev/json_dto/`、`dev/test/`、`dev/sample/`、
`dev/cmake/`），仓库根只有 `LICENSE`/`README.md`/`THANKS`/`externals.rb` 等外围文件。
GitHub 的 `archive/refs/tags/v.0.3.4.tar.gz` 顶层是 `json_dto-v.0.3.4/`，其内即 `dev/`。
conan `get(..., strip_root=True)` 只剥掉 `json_dto-v.0.3.4/` 一层，源码根是 `dev/`
目录内容的上移，但 `dev/` 本身未剥离 → CMakeLists.txt 实际在 `<source_root>/dev/` 下，
`CMake.configure()` 默认用源码根找不到项目文件。init-build 的本地 work 目录也做过
同样的扁平化（`json_dto-0.3.4.work` 根目录直接是 CMakeLists.txt），因此本地手工
cmake 能过而 conan 缓存里的源码根失败，属「本地可编译 / conan 干净构建失败」的典型
表现。

## 方案

在 `source()` 中 `get(strip_root=True)` 之后检测顶层 `dev/` 目录并扁平化到源码根：

```python
def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)
    dev = os.path.join(self.source_folder, "dev")
    if os.path.isdir(dev):
        for item in os.listdir(dev):
            shutil.move(os.path.join(dev, item), self.source_folder)
        shutil.rmtree(dev)
```

无需改上游源码、无需补丁；`package()`/`package_info()` 按扁平化后的
`source_folder/json_dto/*.hpp` 布局工作。

## 验证

- 修复后 `ohc-run.py conan-verify json_dto 0.3.4` 的 G2（conan create）PASS；
- 同一任务内 G3/G4/L0（含上游测试 20 个 ctest 目标、711 断言全过）通过。

## 适用边界

- 适用于 GitHub tag/release tarball 顶层含 `dev/`（或同类非根构建目录）的仓库；
- 若构建目录名不是 `dev/`（如 `src/` 且 CMakeLists.txt 在 `src/` 下），检测逻辑需按实际名称；
- 若 tarball 顶层是多个并列子项目，不应盲目扁平化，需按目标库定位。

## 反例 / 限制

- E195 描述的是 init-build `_promote_nested_source` 提升 `src/` 时丢失同级目录，属于
  init-build 阶段行为，根因与解法均不同；
- E092/E267 的 `dev/` 提及是 `cmake/` 目录 grep 上下文，与本条「构建树在顶层 dev/」无关；
- JSON_DTO_INSTALL 相关选项、RAPIDJSON include 注入（E451 相关）为独立主题，不并入本条。