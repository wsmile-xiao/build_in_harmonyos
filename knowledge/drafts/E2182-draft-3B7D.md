# E2182 — 裸 Makefile 多程序包:依赖经上游 CMDLINE_* 钩子注入(零 Makefile 修改)

## 错误特征
`No rule to make target 'check'`(无 configure/check 目标);或直改 Makefile 注入路径后
diff 膨胀、难以上游化。

## 触发条件
- 构建系统: 裸 Makefile(无 configure),settings.make 预留 CMDLINE_CFLAGS/
  CMDLINE_CPPFLAGS/CMDLINE_LDFLAGS 命令行钩子
- 阶段: make

## 根因分析
无 configure 的多可执行 Makefile 工程无法走 AutotoolsToolchain 注入工具链;
直接改 Makefile 又违反最小补丁原则。上游 settings.make 通常已预留命令行钩子。

## 解决方案

### 推荐方案
conanfile.build() 直接 `make CC=<conf 编译器> CMDLINE_CPPFLAGS=<依赖 include 聚合>
CMDLINE_LDFLAGS=<依赖 lib 聚合>`;依赖路径遍历 self.dependencies 的 cpp_info 去重聚合。
要点:
1. 编译器从 self.conf.get("tools.build:compiler_executables") 读出后拼进命令行
   (勿用 save_script,见 E2180);
2. basic_layout 下裸 Makefile 在 source_folder 原地编译,package() 从 source_folder 取产物;
3. 命令行 PROGRAMS 赋值会抑制 Makefile 内 `PROGRAMS+=x` 条件追加,裁剪/显式包含时
   要显式列出受影响目标。

### 禁止做法
- ❌ 修改 Makefile 注入路径
- ❌ 引用共享系统前缀(R49:路径一律来自各依赖 cpp_info)

## 实证
chiark-utils/8.0.1(12 程序)全流程通过,零 Makefile 修改(conan-create.log)。
E501(单库直连编译)的多程序扩展。
