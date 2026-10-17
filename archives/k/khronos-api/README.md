# khronos-api

Khronos API 规范头文件集合（OpenGL 4.6 / GLES），版本 4.6-git20220505（2022-05-05 快照）。

## 适配说明（4.6-git20220505）

- 来源：Debian 官方包 `khronos-api_4.6+git20220505-1`（Khronos 头文件的官方分发
  途径之一；上游 KhronosGroup 以 XML 注册表 + genheaders.py 生成头文件，本包
  内容与其一致，sha256 固定校验）。
- 产物：`include/khronos-api/{GL,GLES,GLES2,GLES3}` 头文件（glcorearb.h、glext.h、
  gl.h、gl2.h、gl3.h 等 10 个）+ `share/khronos-api/xml`（API 注册表 XML）。
- 纯头文件包（无编译），`header-library` 类型，无依赖。

## 关键适配点（实测）

1. **头文件来源**：上游头文件由 genheaders.py 从 XML 注册表生成，该脚本依赖
   lxml 模块，鸿蒙 Python 无可用 lxml（pip 无鸿蒙 wheel 且源码编译不可行，
   实测安装失败）——改用 Debian 官方二进制包内容（头文件与 XML 均为上游
   发布物，sha256 固定校验保证一致性）。
2. **deb 解析**：deb（ar 格式）在 source() 中用纯标准库（python tarfile +
   手动成员路径检查）解析提取 data.tar.xz，不依赖外部 ar 工具，CI 兼容。
3. **头文件布局**：保持 Debian 原样（`include/khronos-api/GL/...`），消费方以
   `#include <khronos-api/GL/glcorearb.h>` 引用，避免与系统 GL 头命名冲突。

## 验证

- 本地完整验证：conan create → test_package 编译消费头文件
  （`GL_VERSION_4_6` 宏断言）通过。
