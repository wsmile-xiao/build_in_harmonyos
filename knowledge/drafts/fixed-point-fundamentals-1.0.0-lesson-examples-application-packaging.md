# fixed-point-fundamentals 1.0.0 — 教学/示例类仓库（无库产物）按 application 型打包 + 多命令 commands.json

> 草稿（DRAFT，路径 B 候选）— 随 fixed-point-fundamentals 1.0.0 归档 PR 交付，经审核后可 promote 为正式条目。

## 问题

教学课程/示例集合类仓库（如 Fixed-Point Fundamentals：8 课时、17 个独立示例程序）
无头文件、无 .a/.so 库产物、无 configure。conan-init 默认生成 library + autotools
模板，套用必然失败：

```
ERROR: configure script not found          # 纯 Makefile 项目没有 configure
# 且 package_type=library 让 CI 按库形态校验（libs/头文件），test_package 无库可链接
```

## 根因

这类仓库的"产物"是示例可执行程序而非库 API，本质是 **application（工具集合）**，
不是 library。套用库/autotools 流程属于形态错配：
- autotools 模板需要 configure（不存在）→ G2 conan create 失败；
- library 形态需要 cpp_info.libs/头文件（不存在）→ L0 门禁与 test_package 无法落实；
- 产物含可执行文件却不声明 commands.json → L0k/R38 拦截（CI 门禁）。

## 方案

打包四要素（fixed-point-fundamentals 1.0.0 实测）：

```python
package_type = "application"
settings = "os", "compiler", "build_type", "arch"

def build(self):                              # 无 configure，直接跑上游 Makefile
    cc = self.conf.get("tools.build:compiler_executables", {}).get("c") or "clang"
    self.run(f'make examples CC="{cc}" CFLAGS="..."', cwd=self.source_folder)

def package(self):                            # 17 个示例 ELF 拍平安装到 bin/
    copy(self, "lessons/*/examples/*", src=self.source_folder,
         dst=os.path.join(self.package_folder, "bin"),
         keep_path=False, excludes=("*.c", "*.md", "Makefile", "*.o"))
    copy(self, "README*", src=self.source_folder, dst=...share/doc/...)

def package_info(self):
    self.cpp_info.libs = []; self.cpp_info.includedirs = []
    self.cpp_info.libdirs = []; self.cpp_info.bindirs = ["bin"]
```

软件级 `archives/f/fixed-point-fundamentals/commands.json` 多命令声明：

```json
{ "name": "fixed-point-fundamentals", "type": "tool",
  "versions": { "1.0.0": { "ref": "fixed-point-fundamentals/1.0.0",
    "binary": false, "commands": [ "accumulation_drift", "...", "format_selector" ] } } }
```

test_package 不链接库，改为运行安装产物：`test.sh`（冒烟：命令存在、运行 exit=0、
输出非空）+ `ohos_test.sh`（OHOS 专项：重复运行输出 SHA-256 逐位一致 + 关键定点
数值断言——验证该课程"跨平台 bit-identical"卖点）。

## 验证

- conan-verify G0-G4 + L2/L4/L5 全过（可标记 published）；
- conan create 中 test_package 双脚本执行 OK（q16_16_basics/format_selector 等）；
- L0k 校验 commands.json type=tool、name/version 对齐通过；
- 17 个示例安装产物逐一运行 exit=0。

## 适用边界

- 仅适用无头文件、无库产物、纯示例/教学/演示程序集合的仓库（lessons/examples/demo 型）。
- 有可链接 API 的库型项目不适用（应走 library 形态）；
- 纯资源/数据包（无编译、装 share/）是 E255 分支——本方案是"有编译 + 可执行产物 +
  application + bin/"分支，二者边界分明；
- 单二进制 CLI 工具（如 aa3d/pico-sdk）commands.json 只需单命令；本方案新增的是
  **多命令列表形态**（busybox 同构，17 条命令逐一声明）。

## 与既有知识关系

- similar_to: E255（resource-data-package：无编译纯资源包）、
  DRAFT-pico-sdk-cli-commands-json-r38（单 CLI 的 commands.json/R38）
- 新增差异: E255 覆盖"无编译 + 纯资源装 share/"，未覆盖"有编译 + 可执行示例程序 +
  package_type=application + bindirs=bin + 多命令 commands.json"；E424/pico-sdk 草稿
  是单二进制 CLI，本方案补多二进制教学/示例集合形态。