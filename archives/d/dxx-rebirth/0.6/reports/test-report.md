# dxx-rebirth 0.6 测试报告

**测试日期**: 2026-08-25
**测试环境**: OpenHarmony PC aarch64，musl libc，Clang 15，Conan 2.29.1
**上游版本**: DXX-Rebirth 0.60.0-beta2（Conan 包版本 0.6）

## 上游测试边界

上游 `0.60.0-beta2` 源码不包含独立单元测试或集成测试套件，也未定义 `test`、`check` 等测试目标。因此上游自动化测试数量为 0；本适配未删除、禁用或修改任何上游测试。

## Conan 构建验证

| 项目 | 结果 |
|------|------|
| `conan create` 交叉编译 | 通过 |
| `d1x-rebirth` 打包 | 通过 |
| `d2x-rebirth` 打包 | 通过 |
| G0-G4 配方门禁 | 通过 |
| W3 本地 CI 模拟 | 通过 |

验证命令：

```bash
python3 /storage/Users/currentUser/.atomcode/skills/build_in_harmonyos/scripts/ohc-run.py conan-verify dxx-rebirth 0.6
python3 /storage/Users/currentUser/.atomcode/skills/build_in_harmonyos/scripts/ohc-run.py finish dxx-rebirth 0.6 built
```

## 适配后消费侧测试

`test_package/test_commands.py` 在 Conan 运行环境中真实执行打包产物，不依赖专有游戏数据。

### 用例 1：d1x-rebirth 帮助接口

| 项目 | 内容 |
|------|------|
| 命令 | `d1x-rebirth -help` |
| 断言 | 可执行文件存在、20 秒内退出、退出码为 0、输出包含帮助/选项/项目标识 |
| 结果 | 通过 |

### 用例 2：d2x-rebirth 帮助接口

| 项目 | 内容 |
|------|------|
| 命令 | `d2x-rebirth -help` |
| 断言 | 可执行文件存在、20 秒内退出、退出码为 0、输出包含帮助/选项/项目标识 |
| 结果 | 通过 |

### 用例 3：SDL 视频、软件渲染与事件路径

| 项目 | 内容 |
|------|------|
| 命令 | `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./test_sdl_runtime` |
| 断言 | SDL 视频初始化成功、创建 64×48 软件表面、填充并翻转帧、用户事件入队出队一致 |
| 结果 | 通过 |

## 测试汇总

| 指标 | 数量 |
|------|------|
| 上游自动化测试 | 0 |
| 保留并执行的上游测试 | 0 |
| 适配后新增消费侧测试 | 3 |
| 通过 | 3 |
| 失败 | 0 |
| 适配后测试通过率 | 3/3（100%） |

`conan create`、G0-G4 和 W3 属于构建与质量门禁，不虚增计入测试用例数量。

## 已知边界

- 未启动实际游戏流程，因为运行游戏需要用户合法持有的 Descent 或 Descent II 数据文件。
- OpenGL 和 SDL_mixer 可选路径未启用；软件渲染、SDL 视频初始化和事件队列已由消费侧测试覆盖。
- 实际游戏流程仍需用户合法持有的数据文件，因此未纳入自动化测试。
