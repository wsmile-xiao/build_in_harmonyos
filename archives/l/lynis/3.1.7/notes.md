# lynis 3.1.7 适配笔记

## 编译环境
- 构建系统: custom（lynis无标准构建系统，创建了configure + Makefile.in包装器）
- 编译日期: 2026-07-02
- 编译器: N/A（纯shell脚本，无需编译器）
- 状态: published

## 编译步骤

1. **init-build**: 下载 lynis-3.1.7 源码包（来自 downloads.cisofy.com 官方下载站）
2. **创建构建包装器**: 由于 lynis 无标准构建系统，创建了 `configure` 脚本和 `Makefile.in` 包装器，提供 `./configure && make install` 标准流程
3. **make install DESTDIR staging 验证**: 使用 `make install DESTDIR=<staging_dir>` 将 lynis 脚本和数据文件安装到暂存目录，验证安装路径结构
4. **make check 语法检查**: 执行 `sh -n lynis` 对主脚本进行 shell 语法检查，确保无语法错误
5. **conan-init 生成配方**: 使用 conan-init 生成 conanfile.py 配方文件，配置源码下载、构建（replace_in_file 修改）、打包（copy 安装文件）
6. **conan-verify 验证**: 运行 conan-verify 8道门禁全 PASS
7. **finish 收尾**: 生成补丁文件、归档元数据、最终发布

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | shebang `/bin/sh` 在 OHOS 不可用 (E165) | OpenHarmony 系统中 `/bin/sh` 不存在或指向 mksh，mksh 执行 lynis 脚本会挂起 | 将 shebang 改为 `#!/data/service/hnp/bin/bash` |
| 2 | 安全检查 `read` 阻塞 | lynis 在安全审计过程中使用 `read -r void` 等待用户输入，在非交互式环境中会阻塞 | 改为非阻塞读取 `read -r void < /dev/null 2>/dev/null || true` |
| 3 | `--version` 在初始化后才解析 | lynis 原始代码在完成全部初始化后才处理 `--version` 参数，导致非交互式环境下超时 | 添加早期 `--version` 处理逻辑，在初始化前直接输出版本并退出 |
| 4 | conan 包路径找不到数据文件 | lynis 默认从 CWD 和系统路径搜索 include/db/plugins，conan 安装路径不在搜索范围内 | 添加 `SCRIPT_DIR` 变量，将脚本相对路径加入搜索目标 |

## 源码修改

共 3 个补丁文件：

1. **0001-Makefile.in.patch** — 修改 Makefile.in 包装器，适配 OpenHarmony 安装路径
2. **0002-configure.patch** — 修改 configure 包装器脚本，适配 OHOS 环境
3. **0003-lynis.patch** — 修改主 lynis 脚本：shebang 修复、非阻塞 read、早期 --version 处理、SCRIPT_DIR 路径搜索

## 依赖版本

无编译依赖（纯shell脚本工具）

## 验证结果

```bash
# conan-verify 8道门禁全 PASS
$ python3 ohc-run.py conan-verify lynis 3.1.7
[OK] Gate 1: conanfile.py exists and is valid
[OK] Gate 2: conandata.yml exists and has sources
[OK] Gate 3: recipe syntax check passed
[OK] Gate 4: source download and sha256 verified
[OK] Gate 5: build() method present
[OK] Gate 6: package() method present
[OK] Gate 7: test_package exists
[OK] Gate 8: manifest.yaml valid
All 8 gates PASSED

# L2 smoke test
$ lynis --version
Lynis 3.1.7
```

## 注意事项

- lynis 是纯 shell 脚本工具，无 ELF 文件，L4 安全扫描自动通过
- shebang 必须使用 `/data/service/hnp/bin/bash`，不能用 mksh（mksh 会导致 lynis 脚本挂起）
- 所有源码修改通过 conanfile.py 的 `replace_in_file()` 在构建时完成，conandata.yml 的 patches 为空（不用 patch 机制）
- patches/ 目录下的 3 个补丁文件仅作为文档归档，不被 Conan patch 机制应用
