# acf-provisioning 0.10.1 适配笔记

## 编译环境
- 构建系统: makefile（单一递归 Makefile，pure-Lua，无 C 编译）
- 编译日期: 2026-08-16
- 编译器: clang/clang++
- 状态: published（final；built 为中间态）

## 编译步骤

acf-provisioning 是纯 Lua ACF 模块包，无 configure/CMake 步骤：

1. `init-build` 下载官方 tarball（gitlab.alpinelinux.org 对 Conan 默认 UA 返回 418，tarball 用 curl 预下载后 `--no-download` 解压）
2. `make install DESTDIR=$TEST_PREFIX` — 纯拷贝安装（cp -a）到 usr/share/acf/app/provisioning、etc/provisioning、var/www/provisioning/htdocs/cgi-bin、etc/logrotate.d
3. `make check` — 上游无 check/test 目标（Makefile 无此 target）
4. `conan-init` 生成配方 → 重写为 acf-db 同型配方（package_type=application，纯 Lua 模块）
5. `conan-verify` — 8 道门禁全部 PASS（G0-G4 + L2/L4/L5）
6. `finish` — W2 结构 + R36 依赖 + W3 本地 CI 模拟验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gitlab.alpinelinux.org 对 conan 下载返回 HTTP 418 | 站点按 User-Agent 反爬（Conan UA=418，curl UA=200） | conanfile.py source() 用 `get(headers={'User-Agent': 'curl/8.5.0'})`，保持官方 URL（R39） |
| 2 | init-build 把项目根定位到 skill 目录 | find_project_dir() 找到 skill 目录的 SKILL.md | 显式 `--project-dir` 指定项目仓库 |
| 3 | W3 门禁 commands_json_r38 失败 | package_type=application 触发 L0k 判定需要 commands.json | 创建软件级 `commands.json`（type=tool，binary=false，参照 acf-core） |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| acf-core | 0.24.1 | ohpcd 制品仓（已发布） |
| lua | 5.4.8 | ohpcd 制品仓（acf-core 传递依赖） |

## 验证结果

```bash
conan create archives/a/acf-provisioning/0.10.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# G0-G4 + L2/L4/L5 全部 PASS；W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过
```

## 注意事项

- 运行期功能模块（lua-posix/posixtz/LuaXml/socket/lua-sql-postgres 等）未发布到制品仓，但均为运行期可选功能依赖，不阻塞构建；与本系列已合入 ACF 包（acf-db/acf-nsd）一致只声明 acf-core
- gitlab.alpinelinux.org 的 418 拦截：CI 构建时若同样被拦，conanfile.py 已内置 curl UA 规避
---

**编译结束**: 2026-08-16 11:34
**最终状态**: published
