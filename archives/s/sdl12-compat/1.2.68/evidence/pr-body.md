## PR 信息
- **三方库名称**：sdl12-compat
- **上游版本**：1.2.68
- **上游仓库地址**：https://github.com/libsdl-org/sdl12-compat
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（未新增知识草稿）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元/功能测试程序 | 32 | 上游 `test/` 目录的 32 个 `.c` 程序；上游未注册 CTest |
| 集成测试 | 0 | 上游没有独立集成测试框架 |
| 其他测试 | 0 | 无 |
| **合计** | **32** | 全部 32 个程序均完成 HarmonyOS PC 编译 |

### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

配方只显式调用上游原始可执行文件并提供固定参数，没有删除测试、修改测试源码、篡改预期或将超时当作成功。

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游单元/功能测试程序 | 32 | 不变 | 32/32 编译；14 个适合无人值守环境的程序真实执行并通过 |
| 集成测试 | 0 | 不变 | 上游无独立集成测试框架 |
| 鸿蒙特有测试 | 1 | 新增 | Conan `test_package`，包含 9 项真实消费者断言 |
| **合计** | **33** | **+1** | 14 个上游程序和 1 个消费者程序真实执行 |

---

## 上游测试用例修改说明

未修改任何上游测试源码。上游已有 32 个测试程序；新增 `test_package/test_sdl12_compat.c` 是 HarmonyOS Conan 真实消费者验证，不替换上游测试。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

上游已有 32 个测试程序。适配新增的 Conan 消费者测试用于验证 HarmonyOS 包集成和包内 SDL2 运行时加载，不属于“上游无测试后的补全”。

## 文件改动记录

| 范围 | 改动 | 原因 |
|---|---|---|
| `archives/s/sdl12-compat/1.2.68/` | 配方、补丁、元数据、消费者测试和 Markdown 证据 | 完成 HarmonyOS PC 路径 A 适配及扩大上游测试执行覆盖 |
| `feedback/SKILL_FEEDBACK_34c431cd.md` | 更新流程、测试和 CI 状态 | 按 SKILL 反馈规范记录真实执行过程 |

未修改 `SKILL.md`、`references/`、`templates/`、`scripts/`、`ci/`、`SUMMARY.md` 等基础设施文件。

## 验证结果

### 编译验证
- 编译器: HarmonyOS clang 15.0.4
- 编译状态: 通过
- 构建系统: CMake + Conan 2
- 配置选项: `SDL12TESTS=ON SDL12DEVEL=ON STATICDEVEL=OFF`
- 上游测试用例通过率: 14/14（100%）；另 18 个设备/交互程序全部编译并逐项说明未执行原因
- 新增测试用例通过率: 1/1（100%，内部 9 项断言全部通过）

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | 32 个上游测试程序及兼容库均构建成功 |
| 产物存在性 | ✅ | `libSDL-1.2.so`、相对 SONAME 链接、`libSDL2-2.0.so.0`、头文件、pkg-config、`sdl-config` 和许可证齐全 |
| ELF 格式 | ✅ | 两个共享对象均为 AArch64 ELF64 DYN，SONAME 正确且含 `.codesign` |
| 运行测试 | ✅ | 14/14 上游无人值守程序及 1/1 Conan 消费者通过 |
| 动态依赖 | ✅ | NEEDED 仅允许相对系统库 `libc.so`，无 RPATH/RUNPATH；消费者确认加载包内 SDL2 |

### 补丁说明

`patches/0001-use-conan-sdl2.patch` 将上游 SDL2 发现改为使用 Conan 声明依赖，并为 HarmonyOS 恢复 Unix 风格 SONAME 与相对符号链接。未修改上游测试源码。

### 依赖

- `sdl2/2.30.10#9a6fd1dbbc0ac1eef2a42639df48e3b4:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#96027f33d6086703ce6fe4e4502533b3`
- 依赖选项锁定 `shared=False`；从已发布 PIC 静态制品以 `--whole-archive -z defs` 重建包内私有 `libSDL2-2.0.so.0`
- 包内同时交付 sdl12-compat 与 SDL2 的 Zlib 许可证

### 测试结论
- 总体评价: 32/32 上游程序完成编译；14 个可无人值守程序真实执行并 14/14 通过；新增 Conan 消费者 1/1 通过。覆盖版本、平台、错误状态、iconv、RWops、键名、动态加载、线程、视频信息、软件 blit、信号量、timer、摇杆枚举、surface、event 及包内运行时加载。
- 已知限制: 12 个程序等待真实窗口/键鼠事件，2 个需要真实音频或 CD-ROM，2 个需要 OpenGL/GPU 且等待人工退出，`testgamma` 在 dummy 后端明确不支持，`testlock` 是只能由外部信号终止的无限压力循环。它们均完成编译，未被虚报为通过；逐项说明见 `evidence/upstream-test-matrix.md`。

### 遇到的问题与解决方案

1. 已发布 SDL2 仅提供 PIC 静态制品，而 sdl12-compat 按上游设计运行时 `dlopen` SDL2：锁定完整 SDL2 制品引用，重链接并签名私有共享运行时。
2. HarmonyOS CMake 未为该项目自动生成 Unix SONAME：补丁显式传入相对 SONAME，并在包内创建相对链接。
3. Conan home 在本地与 CI 不同：消费者不匹配绝对 home，而按稳定 package-directory 后缀对照 `/proc/self/maps`。
4. 人工审查指出仅执行 4/32：逐个分析并实测全部候选，扩展为 14 个确定性程序；对余下 18 个给出程序级技术原因，不以编译或超时冒充通过。
5. PR #5398 因新增 R40 精确分支门禁阻断：本 PR 使用任务要求的 `fix/sdl12-compat-1.2.68`。

### 验证命令
```sh
conan create archives/s/sdl12-compat/1.2.68 \
  --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='sdl12-compat/1.2.68@ohpcd/stable'

python3 scripts/ohc-run.py graph validate --project-dir "$PWD"
git diff --check
```

远程 CI 证据以 PR #5419 最新机器人结果为准；此前 CI #25780 已通过旧的 4 程序执行集，本次扩大测试清单后将重新触发完整 CI。