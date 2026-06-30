# attr

Extended attribute (xattr) 工具集，提供对文件系统扩展属性的读取、设置和删除功能。

## 功能概述

- **getfattr** — 读取文件或目录的扩展属性
- **setfattr** — 设置或修改文件或目录的扩展属性
- **attr** — 旧版扩展属性操作接口
- **libattr** — 扩展属性操作的 C 库 (libattr.a)

## OHOS 适配

| 适配点 | 说明 |
|--------|------|
| 平台识别 | config.guess/config.sub 需添加 HarmonyOS 识别 (E007/E072) |
| 文件系统兼容 | configure 中 umask 077→022，修复 HMDFS UID 映射导致的临时文件权限问题 |
| 静态编译 | attr 是系统同名库，按 R26 使用 `--disable-shared` 静态编译，避免污染 /lib |
| 测试限制 | make check 2/2 FAIL — HarmonyOS 不完全支持 user.* xattr namespace，部分 syscall 未实现 (SIGSYS) |

## 依赖关系

- 编译依赖：无（attr 是独立工具库）
- 运行依赖：无

## 参考资料

- 官网：https://savannah.nongnu.org/projects/attr/
- 源码：https://download.savannah.nongnu.org/releases/attr/
