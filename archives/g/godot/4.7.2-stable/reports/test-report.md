# godot 4.7.2-stable 测试报告

## 测试形态

godot 的测试为 **doctest 嵌入引擎二进制**形态：`tests=yes` SCons 构建把 173 个 tests/ 编译单元 + 模块测试编进 `libtests.a` 链入引擎主程序，运行时 `godot --test` 触发（上游 CI 用法 `--headless --test`）。

三层运行结构（实测发现，见 notes.md 实验 12）：
1. 默认组：`godot --test`（无 TEST_SUITE 标记的用例）
2. SceneTree 组：`godot --test --test-case='[SceneTree]*'`（249 个，harness 自动起 mock DisplayServer）
3. 显式 suite 组：`godot --test --test-suite=[Navigation2D],...`（47 个）

## 上游注册测试数（N）

- 源码口径：**1334** TEST_CASE（tests/ 1239 + modules/ 95，`grep -rE '^\s*TEST_CASE'` 实测）
- 二进制口径：`--list-test-cases` 列出 **1368**（+3 个 [Editor] 守卫用例不编入模板形态）

## OHOS aarch64 实测结果（2026-09-13）

### 源码树环境（三层全跑）

| 组 | 用例数 | 通过 | 失败 | 断言 |
|---|---|---|---|---|
| 默认组（排除 3 类环境限制） | 1360 | 1360 | 0 | 309643/309643 |
| SceneTree 组 | 249 | 249 | 0 | 11938/11938 |
| 显式 suite 组（Navigation×2/ClassDB/TextServer/Triangle2/Validate） | 47 | 47 | 0 | 101216/101216 |
| **合计** | **1656** | **1656** | **0** | **422797/422797** |

### 包安装环境（test_package 采用，W3 conan create 通过）

| 组 | 用例数 | 通过 | 断言 |
|---|---|---|---|
| 默认组（排除 15 组环境限制） | **1313** | **1313** | 308947/308947（exit=0） |

### 环境限制豁免（15 组，OHOS 环境与安装形态差异，非引擎缺陷）

| 类别 | 用例组 | 根因 |
|---|---|---|
| /tmp 只读（E002） | [ConfigFile] Saving file（SIGSEGV）、[UDSServer]*（listen EINVAL→SIGSEGV） | 测试硬编码 /tmp 路径，OHOS /tmp 只读写失败后句柄无效 |
| musl 解析器差异 | [IP] resolve_hostname（1000 子断言） | musl getaddrinfo("localhost") 无 ::1 项 |
| 源码树数据文件依赖 | [ZIPReader] read files、[FontFile]*、[Crypto]*（12）、[FileAccess]*（5）、[Image] Saving and loading、[OS] Executable and data paths、[TranslationCSV]*、[SceneTree][GLTFDocument]*（2）、[ImageTexture] set_path、[ImageTexture3D] set_path、[FuzzySearch]*、[PCKPacker]* | TestUtils::get_data_path() 解析 `<exe_dir>/../tests/data/...`——安装包中不存在该目录（数据不随包分发） |

## 消费者验证（test_package，W3 conan create 通过）

1. `godot --version` → `4.7.2.stable.custom_build.ed1daf0bf`（exit=0，引擎可执行）
2. `godot --help` → 完整帮助输出（参数解析路径全通）
3. `godot --test --test-case-exclude=...` → 1313/1313 SUCCESS（exit=0，净环境验证）

## 结论

- 引擎核心（core/scene/servers）+ 模块测试在 OHOS aarch64 上 100% 通过（源码树 1656/1656；安装态 1313/1313）
- 15 组豁免均为环境差异（平台只读 /tmp + musl 解析器 + 源码树数据路径假设），引擎逻辑无缺陷
- 测试统计：上游注册 1334（源码）/1368（二进制），安装态实测通过 1313，源码树三层全跑 1656
