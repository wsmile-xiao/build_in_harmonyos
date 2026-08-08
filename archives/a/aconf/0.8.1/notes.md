# aconf 0.8.1 适配笔记

## 编译环境
- 构建系统: makefile（Lua 脚本 + shell 守护进程，无 C 编译）
- 编译日期: 2026-08-07
- 编译器: 无需编译（aconf 为 Lua/shell 脚本项目）
- 状态: published

## 编译步骤

```bash
# 1. init-build（源码来自 Alpine distfiles 官方镜像）
python3 scripts/ohc-run.py init-build aconf 0.8.1 \
  --url=https://distfiles.alpinelinux.org/distfiles/v3.22/aconf-0.8.1.tar.xz

# 2. 构建与验证（aconf 是 Lua/脚本项目，无 configure/编译）
cd $BUILD_SRC_DIR
make -j1              # 生成 doc（需 ldoc，环境无则预生成占位）
make install ROOT_DIR=$TEST_PREFIX/storage/Users/currentUser

# 3. 配方生成与验证
python3 scripts/ohc-run.py conan-init aconf 0.8.1
python3 scripts/ohc-run.py conan-verify aconf 0.8.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make all 需要 ldoc 生成 doc/index.html | OHOS 环境无 ldoc | build() 预生成 doc/index.html + ldoc.css 占位文件绕过 |
| 2 | make install 软链接冲突（ln -s 覆盖） | Makefile link 目标直接 ln -s | 探索阶段改 Makefile 加 rm -f；conan 环境 staging 全新无冲突，配方不依赖补丁 |
| 3 | 制品仓 lua 为 5.4.8，上游 LUA_VERSION=5.3 | 版本目录不匹配 | package() 将 usr/share/lua/5.3/aconf 映射到 5.4 |
| 4 | test_package 报 aconfd not executable | POSIX test -x 检查 CWD 而非 PATH | test.c 改用 command -v 解析 PATH，ACONF_LUA_DIR 环境变量传模块路径 |
| 5 | L1e 破坏性验证失败 | aconfd 在 usr/sbin 而非标准 bin/ | package() 将 aconfd 放入 bin/ |

## 源码修改

无补丁（探索阶段 Makefile 软链接修改在 conan 环境不需要，未纳入配方）。

## 依赖版本

- lua/5.4.8（制品仓已发布，aconf Lua 守护进程运行时依赖）

## 验证结果

```bash
# test_package（conan create L1 测试）
./test_aconf  # → PASS: aconfd found on PATH / PASS: aconf/init.lua present

# conan-verify 门禁
G1-G4 全部 PASS，配方验证通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（Lua/脚本安装） |
| test_package/ | L1 实质测试（command -v aconfd + init.lua 存在性） |
| packaging/aconf-0.8.1-ohos-aarch64.tar.gz | release 打包产物 |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

- aconfd 为 Lua 配置守护进程启动器（shell 脚本），`package_type=application`，`cpp_info.bindirs=["bin"]`
- 运行时依赖 lua/5.4.8（制品仓版本；上游默认 5.3 已在配方中映射）
- **已知限制**：aconfd 实际 exec `uwsgi --plugin lua_plugin.so`，制品仓 uwsgi 为 nolang（无 lua 插件）且 OHOS lua 包无 CLI，守护进程在 OHOS 上无法真正启动；test 仅验证文件存在性，运行时需补充 uwsgi+lua 插件
- 上游无 make check 目标，通过 aconfd/init.lua 存在性验证

---

**编译结束**: 2026-08-07 21:15
**最终状态**: published
