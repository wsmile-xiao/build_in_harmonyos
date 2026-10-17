# nbsdgames 6.0.2.1 编译进度

**日期**: 2026-08-16
**状态**: ✅ 编译成功

## 版本说明

6.0.2.1 为 6.0.2 的版本递增修复版（R37：已发布版本不可变，修复须递增版本号后缀）：

- conandata.yml `sources.url` 恢复为单一官方 GitHub URL（R39：不手动加镜像前缀，镜像 fallback 由 CI 自动生成）
- conanfile.py `version` 递增为 6.0.2.1
- 同步更新 commands.json、软件级/版本级 manifest.yaml、test_package/MANIFEST.yml 引用

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | init-build 成功，下载解压完成 |
| Step 2 make | ✅ | make CC=clang 编译完成 |
| Step 3 install | ✅ | 安装到 staging 目录 |
| Step 4 package | ✅ | 打包为 ohos-aarch64 tar.gz |
| Step 5 test_package | ✅ | sudoku -h 消费者验证 PASS |

## 发现与知识

1. **Makefile 构建**: nbsdgames 使用简单的 Makefile 构建系统，无需 autotools。
2. **ncurses 依赖**: 依赖 ncurses 宽字符静态库，构建时需要显式传入 include/lib 参数。
3. **安装路径**: 通过 GAMES_DIR/SCORES_DIR/MAN_DIR 变量控制安装位置。
4. **版本治理**: 制品仓已发布版本（6.0.2）的 recipe 被 CI 发布流程改写为镜像列表形式；重新验证/修复须递增版本号（6.0.2.1）并恢复单一官方 URL，避免 L0j 版本碰撞门禁误判与 R39 违规。

---

**编译结束**: 2026-08-16
**最终状态**: built
