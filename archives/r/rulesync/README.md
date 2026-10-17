# rulesync

Unified AI rules management CLI tool — 从统一源（`.rulesync/`）为 Cursor / Claude
Code / Copilot / Cline / Windsurf / JetBrains AI Assistant / Amp / Hermes 等
各类 AI 开发工具生成规则、命令、子代理、技能与配置文件。

- 上游仓库：https://github.com/dyoshikawa/rulesync
- 官方发行渠道：npm（`registry.npmjs.org/rulesync`）
- 许可证：MIT

## 包形态

`package_type = application`，产物布局：

```
bin/rulesync                      # launcher: exec node --jitless res/rulesync/dist/cli/index.js "$@"
res/rulesync/dist/                # 上游 npm 发布包的 bundle 产物（ESM + CJS + d.ts）
res/rulesync/node_modules/        # 运行时依赖树（16 条直接依赖展开，共 258 包）
res/rulesync/package.json
licenses/LICENSE
```

## 依赖模型

- **Node.js 运行时**：由 worker 提供（cmd-pkgs 预装，`engines.node >= 22`），
  **不是** Conan 依赖；与 bruno-cli / uglify / svgo 等先例一致。
- **npm 依赖**：由 `npm install --ignore-scripts --omit=dev` 在 `build()` 中物化，
  随包分发 `node_modules/`。
- **Conan 制品仓强制第三方依赖：0**（详见 `14.2.0/notes.md`）。

## 消费

```bash
rulesync --version          # 14.2.0
rulesync init               # 初始化 .rulesync/ 与 rulesync.jsonc
rulesync generate -t cursor -f rules
```
