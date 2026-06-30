# rolldice 1.16 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -kSL -o rolldice-1.16.tar.gz https://github.com/sstrickl/rolldice/archive/refs/tags/v1.16.tar.gz`
2. 初始化编译环境: `python3 ohc-run.py init-build rolldice 1.16 --url=...`（SSL 证书需手动安装）
3. 进入源码目录: `cd $BUILD_SRC_DIR`
4. 编译: `make CC=clang CFLAGS="-fPIC -O2"`
5. 安装到 Staging: `make install DESTDIR=$TEST_PREFIX`
6. 运行测试: `cd tests && bash tests.sh`
7. 生成 Conan 配方: `python3 ohc-run.py conan-init rolldice 1.16`
8. 验证 Conan 配方: `python3 ohc-run.py conan-verify rolldice 1.16`
9. 收尾: `python3 ohc-run.py finish rolldice 1.16 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书下载失败 | 鸿蒙环境缺少 CA 证书 | 手动 `curl -kSL` 下载 cacert.pem 到 /usr/local/ssl/cert.pem |
| 2 | readline 库不可用 | Conan remotes 无 readline 包，系统未预装 | 修改源码用 getline() 替代 readline()，生成 3 个补丁 |
| 3 | Conan EnvVars.save() 报错 | Conan 2.12 API 变更 | 改用 `envvars.save_script("rolldice_env")` |
| 4 | make 找不到 Makefile | basic_layout 分离源码/构建目录 | 改用 `make -j1 -C {self.source_folder}` |
| 5 | make -j2 jobserver 失败 | 鸿蒙 mkfifo 权限限制 (E046) | 改用 `make -j1` |
| 6 | test_package deps_env_info 报错 | Conan 1 API 在 Conan 2 中不存在 | 改用 `self.dependencies["rolldice"].package_folder` |
| 7 | GitHub 下载超时 | 中国大陆网络访问 GitHub 不稳定 | conandata.yml URL 改用 ghfast.top 镜像 |

## 源码修改

### 补丁 1: 0001-Makefile.patch
- 文件: Makefile
- 修改: `LIBS = -lreadline` → `LIBS =`（移除 readline 链接依赖）

### 补丁 2: 0002-main.c.patch
- 文件: main.c
- 修改: 在 `roll_from_interactive()` 前添加 `readline()` 替代函数，使用 `getline()` 实现相同接口（返回 malloc'd 字符串，NULL 表示 EOF，去除末尾换行符）

### 补丁 3: 0003-rolldice.h.patch
- 文件: rolldice.h
- 修改: 移除 `#include <readline/readline.h>`，替换为注释

**修改原因**: GNU readline 库在 Conan remotes (@ohpcd/stable) 中不可用，且任务标注"依赖: 无"。readline() 仅用于从 stdin 读取行，getline() 可完全替代。

## 依赖版本

无外部依赖。原依赖 readline 已通过源码补丁移除。

## 验证结果

### 编译验证
```bash
$ make CC=clang CFLAGS="-fPIC -O2"
# 编译成功，1 个警告 (isdigit 隐式声明，不影响功能)
$ echo $?
0
```

### 测试验证 (tests/tests.sh)
```bash
$ bash tests.sh
# 23 个测试用例全部通过 (RC=0)
```

### Conan 包二进制验证
```bash
$ file rolldice
ELF executable, 64-bit LSB arm64, static, not stripped
$ readelf -d rolldice
# 无动态段（完全静态链接，R26 通过）
$ rolldice -v
rolldice, v1.16
$ rolldice 1d6
5
$ rolldice 1d999999999
rolldice: Requested number of dice faces is too large
# 退出码 65 (EX_DATAERR)
```

### Conan 验证门禁 (8/8 通过)
- G0: PASS (预构建风险评估)
- G1: PASS (配方完整性)
- G2: PASS (conan create 干净构建)
- G3: PASS (静态链接 R26)
- G4: PASS (产物完整性)
- L2: PASS (smoke test)
- L4: PASS (checksec 安全扫描)
- L5: PASS (产物基线对比)

## 注意事项

1. **readline 替代**: readline() 替代函数不支持行编辑/历史功能，但功能测试全部通过
2. **编译警告**: rolldice.c 中 isdigit() 未包含 <ctype.h>，产生隐式声明警告，不影响功能
3. **静态链接**: Conan 包二进制为完全静态链接（无动态段），R26 通过
4. **ghfast.top 镜像**: conandata.yml 中 URL 使用 ghfast.top 镜像以解决 GitHub 下载超时
5. **make -j1**: 鸿蒙环境 make jobserver mkfifo 权限限制，必须使用 -j1

---

**编译结束**: 2026-06-30 12:55
**最终状态**: published
