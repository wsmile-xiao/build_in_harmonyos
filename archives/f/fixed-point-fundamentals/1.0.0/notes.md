# fixed-point-fundamentals 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile + 各 lesson 内 Makefile，纯 Makefile 无 configure）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（本机无 gcc）
- 状态: built（验证通过未 upload，与 manifest.yaml 一致）

## 编译步骤

1. init-build 下载官方 tag v1.0.0 tarball（GitHub 直连超时，经镜像获取后核验 SHA-256
   5db7f6533dda80f95aed47aabe3caffc634bcceff8dab868acb13f564de6ac52）
2. 上游无测试框架：make test 仅扫描 lessons/<lesson>/src/tests（全仓库不存在），实例化 0 用例；
   17 个示例程序全部编译并实际运行（exit 0，输出非空）
3. conanfile.py 按 application 型打包：`make examples CC=<toolchain-cc> CFLAGS="<去 -Werror>"`
   → 产物 17 个示例 ELF 拍平安装到 bin/（附 README/LICENSE）
4. 软件级 commands.json 声明 17 个示例命令（R38）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连 urlopen 超时 | 本机无法直连 github.com | 经镜像获取官方 tag tarball，sha256 与官方一致 |
| 2 | 5/17 示例在 `-Werror` 下构建失败 | clang 比 gcc 严格：unused static inline 函数 ×3、int64/int→float/double 隐式转换 ×2 被升级为错误 | 配方构建 CFLAGS 移除 -Werror（保留其余告警），不改上游源码 |
| 3 | Makefile 硬编码 CC=gcc | 本机/CI 无 gcc | 配方从 Conan Toolchain 获取 CC（R33） |
| 4 | /tmp 只读 | OHOS 平台限制（E002） | 日志与临时文件写入 $HOME/tmp |

## 源码修改

无源码补丁（patches/ 为空）；构建期仅覆盖 CC 与 CFLAGS。

## 依赖版本

无第三方依赖（纯 C99，libc 即可）。

## 验证结果

```bash
# 17 个示例全部编译（clang，去 -Werror）并运行 exit=0
make examples CC=clang CFLAGS="-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -O2 -g"
# 逐一运行：17/17 exit=0
# conan create / conan-verify 8 道门禁见 ci_logs
```
---

**编译结束**: 2026-09-21 16:15
**最终状态**: built
