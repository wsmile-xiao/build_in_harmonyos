# slop 7.7 HarmonyOS 适配笔记

## 构建配置

- 上游版本：v7.7
- 构建系统：CMake
- 目标：HarmonyOS/OHOS 6.0，AArch64，Clang 15，libc++
- 依赖：libx11/6.4.0、libxext/6.4.0.1、glm/1.0.3
- `BUILD_SHARED_LIBS=OFF`：工具包静态包含 `libslopy.a`
- `SLOP_OPENGL=OFF`：HarmonyOS PC 不提供上游所需的 GLX 显示栈，保留上游完整 XShape 后端
- `SLOP_UNICODE=OFF`：避免引入非必需 ICU；不影响 ASCII CLI 与选择 API

源码由官方 GitHub tag 下载，SHA-256 为
`a69a6e5c41d7fff1c6aa35b367a5c5a6dc98e621fa9a1908808d6308c2b40f4e`。
源码包仅保存在仓库外的 `docs/refs`，未混入归档。

## W0 依赖检查

下列引用均通过 `conan download <ref> -r=ohpcd --only-recipe` 或等价的
`conan install --build=never` 实测：

- libx11/6.4.0
- libxext/6.4.0.1
- xorgproto/2025.1（传递依赖）
- glm/1.0.3

`libxext/1.3.7` 未发布，因此没有使用；选用已发布且与
`libx11/6.4.0` 同一依赖线的 `libxext/6.4.0.1`。

## HarmonyOS 运行时适配

HarmonyOS 运行环境可能没有当前 UID 对应的 passwd 条目，上游直接解引用
`getpwuid(getuid())` 会在程序初始化配置目录时崩溃。补丁
`0001-src-resource.cpp.patch` 优先使用标准 `HOME` 环境变量，并对 passwd 查询
和最终回退逐层判空。该改动不引入平台宏，也不改变 passwd 正常存在时的行为。

上游 CMake 通过 `GLM_INCLUDE_DIR`、`X11_INCLUDE_DIR` 和 `XEXT_LIBRARIES`
等旧式查找变量接入依赖；这些变量在不同 CMake/Conan 组合中的行为不一致。
构建补丁改用 Conan `CMakeDeps` 生成的 `glm::glm`、`libx11::libx11` 和
`libxext::libxext` 目标，并由 `CMakeToolchain` 管理其 generators 搜索路径，
使头文件、传递依赖和链接信息由目标稳定传播。

## R47 语言预检

`ohc-run.py lang-preflight slop 7.7` 检出 CMake 项目和 26 个 C++ 源文件，
C++ 占比 100%，与任务语言一致。

## R51 上游测试三步法

### 1. 清点

官方 v7.7 tarball 全树检查结果：

- `find . -type d -iname 'test*'`：0
- `find . -iname '*test*'`：0
- `rg 'enable_testing|add_test|ctest|BUILD_TEST'`：0
- 顶层 `CMakeLists.txt`：无测试目标、无测试子目录

所以源码声明的上游测试数 N=0。

### 2. 运行

配方在构建后执行 `ctest --output-on-failure`。由于上游没有注册测试，
CTest 报告空套件，实际可运行上游测试数 N'=0。

### 3. 回填

上游测试 0/0；没有删除、修改、跳过或用消费者测试冒充上游测试。
适配后新增 5 个消费者场景、20 条确定性断言，全部必须通过：

1. C API 默认值和无 DISPLAY 默认值。
2. `slop --version`。
3. `slop --help`。
4. HOME、XDG_CONFIG_HOME 和 DISPLAY 均缺失时的确定性错误路径，覆盖
   HarmonyOS 无 passwd 条目的启动场景。
5. HarmonyOS AArch64 ELF 且不依赖 GL/GLX/GLEW 的平台契约。

## 已知运行边界

HarmonyOS PC 没有 X server，因此交互式窗口/矩形选择需要外部 X11 显示服务。
本适配不把该能力误报为已验证；消费者测试覆盖公共 API、完整二进制加载、
参数解析和确定性无显示服务行为。

## 结束标记

slop 7.7 适配完成，状态：built；上游测试 0/0、新增测试 5/5，全部通过。
