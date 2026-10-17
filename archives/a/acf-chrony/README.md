# acf-chrony

Alpine Configuration Framework（ACF）chrony 应用插件包 —— 基于 Lua 5.4 的 Web 系统管理接口，配置 chrony NTP 守护进程。

- 上游仓库：https://gitlab.alpinelinux.org/acf/acf-chrony
- 构建系统：扁平 Makefile（纯 Lua 应用插件包，无 C 编译）
- 产物：`share/acf/app/chrony/` 下的 Lua controller/model + .lsp 视图模板 + .menu/.roles 声明

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.8.1 | published | 首次适配。conan-verify 通过（G0-G4 + L2/L4/L5），功能测试 92/92 PASS（test_app 34 + test_model 58） |

## 依赖

- conan：`acf-core/0.24.1`（ACF 框架本体，提供 mvc/lib/www + acf-cli CLI 入口 + 共享 .lsp 模板）
- conan：`chrony/4.8`（运行时被配置的 NTP 守护进程）
- 传递依赖：`lua/5.4.8`（经 acf-core）

## 适配要点

- 纯 Lua 应用插件包，与 acf-core 同模式：`make all` 为空，`make install DESTDIR` 仅 `cp -a chrony*` 到 `usr/share/acf/app/chrony/`
- 3 个 .lsp 模板（expert/logfile/status-html.lsp）是符号链接，指向 acf-core 共享模板，运行时由 acf-core 依赖解析
- 上游无测试套件（aports `options="!check"`），自建功能测试实质验证 controller→model 调用链（R34）
- R38 判定：本包不新增独立 CLI 命令（CLI 入口由 acf-core 的 acf-cli 统一提供），软件级 commands.json 声明 `binary: false`
- HMDFS 不支持硬链接，init-build dual-track 复制失败时需手动 `cp -a`（保留符号链接）重建 .work 目录
- gitlab.alpinelinux.org 拦截脚本 UA（HTTP 418），conanfile.py source() 添加 distfiles.alpinelinux.org 镜像 fallback（R39）
