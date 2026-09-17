# cvsgraph

## 简介
cvsgraph 对 CVS/RCS 仓库中单个文件的修订与分支进行图形化渲染，
读取 RCS `,v` 文件，用 libgd 绘制版本树（PNG/GIF/JPEG 及 HTML imagemap），
常与 cvsweb/viewvc 集成使用。命令行工具，无库产物。

## OHOS 适配
- 构建系统 autotools；configure 无 AC_CANONICAL_HOST，交叉编译由 Conan
  工具链环境变量驱动（R1：仅 `--prefix`）
- 依赖 `gd/2.3.3.1`（shared；需 PNG 输出与 FreeType 字体支持）
- 预生成词法/语法文件随包分发，构建不需要 flex/bison
- configure 的 `umask 077` 在 build() 中替换为 022（OHOS 权限坑）
- 上游无测试套件（Makefile.am 无 check/TESTS，证据见 test_package/MANIFEST.yml）

## 排除与替代
无

## 依赖
- 编译工具: clang, make, bash（configure 调用）
- 运行库: gd（含 freetype/libpng 等闭包）

## 功能验证
```bash
# 版本
cvsgraph -V

# 渲染测试（test_package 自带最小 RCS 文件与配置）
cvsgraph -c cvsgraph.conf -o out.png -r "" test.txt,v
# 输出 out.png 应为合法 PNG
```
