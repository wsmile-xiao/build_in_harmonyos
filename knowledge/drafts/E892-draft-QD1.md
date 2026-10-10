# E892（草稿）：分包 Qt 模块的 qmake 库路径校正

## 触发场景与症状

上游 qmake 项目写有 `QT += core5compat`，而 `qtbase` 和 `qt5compat` 是两个独立发布的 Conan 包。源码可能全部编译成功，到最终链接才出现 `qtbase/.../lib/libQt6Core5Compat.so` 不存在；实际同名库位于 `qt5compat/.../lib/`。

## 根因与可复用判断

模块包自带的 `qt_lib_core5compat.pri` 将 `QT.core5compat.libs` 设为 `$$QT_MODULE_LIB_BASE`。独立运行的 qmake 把这个变量解析到自身所在的 `qtbase` 根目录，不会自动理解 Conan 把模块拆到另一包。生成的 Makefile 里是错误的**绝对文件路径**，因此仅补 `LIBS += -L<qt5compat/lib>` 无效。先读生成的 `LIBS`，而不是仅检查库文件或头文件是否存在。

## 修复步骤

1. 在配方构建目录创建私有 `mkspecs/modules` 覆盖层，复制已发布 `qt5compat` 包自己的 `qt_lib_core5compat.pri` 和 private 描述，不修改依赖包。
2. 只把描述中的 `$$QT_MODULE_LIB_BASE`、`$$QT_MODULE_INCLUDE_BASE` 替换为该包真实的 `lib`、`include` 路径。通过 `QMAKEPATH` 指向覆盖层，保留 qmake 对其他 Qt 模块的正常查找。
3. qmake 后立即检查 Makefile 含真实 `qt5compat/lib/libQt6Core5Compat.so`，再执行长时编译、安装包验证。不要在 `qtbase` 包内造链接，也不要删除 `QT += core5compat`。

## QDirStat 证据与边界

- q2：`Translator.cpp` 等源码已通过编译，链接命令却引用 `qtbase/.../lib/libQt6Core5Compat.so`，`clang-15` 报不存在。日志 SHA-256：`8473d7fffff148b5321091d37967359d61f7972e664956917510ed7df84030c2`。
- q3：构建目录覆盖层和 Makefile 路径断言通过，目标机 `conan create` RC 0；上游没有自动化测试目标（`test/` 只有夹具和生成脚本），另加的安装包消费者测试 1/1 PASS。日志 SHA-256：`34c17c43fb5d36c7e7d0ec560ea9372f290ec4131fd47d396d138b5ab4e58705`，冻结事务 validator PASS。
- q1 的 `dgettext` 声明缺失由显式依赖已发布的 `gettext/0.22.5.1` 解决；它与本条的 qmake 模块路径根因不同，不重复申报已有 gettext 知识。

适用于独立 Qt 模块包及 qmake 项目；如果模块仍安装在 qmake 自身的 Qt 前缀，此覆盖层不需要。目标机一次完整成功不等于比赛 CI 已通过，后者需单独观察。
