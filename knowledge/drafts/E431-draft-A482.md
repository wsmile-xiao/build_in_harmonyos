# E431 — CMake 4.x 工具链模式下 add_custom_command 不展开 :: ALIAS 目标名（Error 127）

## 错误特征
- ninja/make 执行生成器命令报 `Error 127`（命令未找到）
- build.make 中 COMMAND 保留 `Zeek::BifCl` 式字面量，未展开为可执行文件真实路径

## 触发条件
- 构建系统: CMake 4.x（4.1.2 实测）
- 阶段: build
- 典型项目: 交叉编译（CMAKE_SYSTEM_NAME 置位）且用 `add_custom_command(COMMAND <ALIAS 目标>)`
  运行 host 生成器工具（词法/语法/绑定生成器及自研工具链）的 CMake 项目

## 根因分析
CMake 4.1.2 在设置 toolchain（交叉模式）后，`add_custom_command(COMMAND ...)` 中 :: 命名空间的
ALIAS 目标名不再展开为可执行文件真实路径，build.make 里保留字面量（`cd ... && Zeek::BifCl ...`）。
host 生成器本身（bifcl/binpac/gen-zam）已真实构建成功且可执行——只有命令行未展开。
交叉编译私有工具链（host 工具 + 目标产物）场景的典型陷阱。

## 解决方案

### 推荐方案（生成器表达式）
把 CMake 源中 `COMMAND Zeek::BifCl / Zeek::BinPAC / gen-zam` 改为
`$<TARGET_FILE:Zeek::BifCl>` 等生成器表达式，generate 期展开真实路径。
重配置后验证 build.make 命令已展开为 `../tools/binpac/src/binpac`，三生成步骤全过。
通用做法，其他 host 生成器目标同样适用，无平台宏。

## 验证
```bash
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=<toolchain.cmake>
grep -n '::' build.make | head     # 出现字面 ALIAS 名 = 命中
grep -n 'TARGET_FILE' build.make   # 应已展开为真实路径
```

## 关联条目
- 同来源: PR #11976（zeek 8.2.1，BifCl/BinPAC/gen-zam 三生成器）
