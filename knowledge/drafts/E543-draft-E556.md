# E543 — find_program 缓存断链符号链接 (glib-mkenums) 导致 idotypebuiltins 生成失败

## 错误特征

```
[  3%] Generating idotypebuiltins.h
/bin/sh: /data/service/hnp/bin/glib-mkenums: No such file or directory
make[2]: *** [src/CMakeFiles/ayatana-ido3-0.4.dir/build.make:78: src/idotypebuiltins.h] Error 126
make[1]: *** [CMakeFiles/Makefile2:128: src/CMakeFiles/ayatana-ido3-0.4.dir/all] Error 2
```

CMake 构建期间，上游 `src/CMakeLists.txt` 的
`find_program(GLIB_MKENUMS glib-mkenums)` + `add_custom_command` 生成
`idotypebuiltins.h` 时执行失败（Error 126 = 命令不存在/不可执行）。

## 触发条件

- 构建系统: cmake
- 阶段: compilation（custom command 执行期）
- 前置: 上游用 `find_program` 定位 glib 构建工具（glib-mkenums/glib-genmarshal/
  gdbus-codegen）；环境 PATH 中先命中一个**断链符号链接**
- 环境: OHOS CI bundle `/data/service/hnp/bin/glib-mkenums` 指向旧版阐库
  `glib_2.38.2`（该路径不存在或已移除）

## 根因分析

CMake 的 `find_program` 在 **configure 期**按 PATH 顺序搜索并**缓存**结果到
`CMakeCache.txt`（如 `GLIB_MKENUMS:FILEPATH=/data/service/hnp/bin/glib-mkenums`）。
CI bundle 中该路径是一个断链符号链接（dangling symlink）：configure 期
`find_program` 认为它"存在"并缓存，build 期实际执行时报
`No such file or directory`（Error 126）。这是「符号链接存在但目标不可达」导致的
缓存误判，与 PATH 中完全缺失工具（E540：runner-path-prepend）机制不同。

## 解决方案

### 推荐方案

在 conanfile.py 的 `generate()` 中，用 CMakeToolchain 变量**显式覆盖**
find_program 缓存，指向 glib 包内真实脚本的绝对路径（同时把 glib 包 bin/ 前置
PATH 兜底）：

```python
def generate(self):
    PkgConfigDeps(self).generate()
    tc = CMakeToolchain(self)
    glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
    tc.variables["GLIB_MKENUMS"] = os.path.join(glib_bin, "glib-mkenums")
    env = Environment()
    env.prepend_path("PATH", glib_bin)
    env.vars(self).save_script("glib_tools_env")
    tc.generate()
```

要点：
- `tc.variables["GLIB_MKENUMS"]` 会写入 CMakeCache 覆盖 find_program 的坏缓存值
- glib 构建工具是 Python 脚本，glib 包内 `/bin/glib-mkenums` 头部为
  `#!/usr/bin/env python3`，可直接绝对路径调用
- 不作为（配方的）构建依赖注入，仅路径覆盖，无需 tool_requires

### 禁止做法

- ❌ 修改上游 CMakeLists（污染上游源码）
- ❌ 依赖 `rm -f /data/service/hnp/bin/glib-mkenums` 之类的环境清理（不可移植、越权）
- ❌ 用 `--no-allow-shlib-undefined` 或跳过 custom command 掩盖失败（伪造跳过）

## 验证

```bash
conan create archives/a/ayatana-ido/0.10.4 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing   # exit 0
# idotypebuiltins.h 正常生成, libayatana-ido3-0.4.so 完整构建
# test_package ctest 1/1 PASS
```

## 四范围查重

- knowledge/graph/: 部分相关但机制不同。E540（runner-path-prepend）是 PATH
  **缺失** hnp bin 导致 `make: not found`；E018/E050/E073 是 HMDFS 软链接
  创建/加载问题，均非 find_program 缓存断链符号链接的场景。
- knowledge/doc/、knowledge/drafts/、index.tsv: 无 find_program 缓存断链条目。
- 结论: 路径 B 成立（新增差异：CMakeToolchain 变量显式覆盖 find_program 缓存）。

## 关联条目

- 相似: E540（runner 路径）, E018/E050（HMDFS 符号链接）
- 来源: ayatana-ido 0.10.4 适配 (r01)