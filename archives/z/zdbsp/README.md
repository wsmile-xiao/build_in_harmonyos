# zdbsp

**ZDoom 独立节点构建器**（ZDoom's node builder）

zdbsp 为 Doom 格式 WAD 地图构建 BSP 节点，也支持 GL 友好节点（GL nodes）、扩展/压缩节点。它是 ZDoom 系列引擎使用的节点构建器，可独立运行，输入一个含地图的 WAD，输出构建好节点的 WAD。

## 用法

```bash
zdbsp [options] sourcefile.wad
```

| 选项 | 说明 |
|------|------|
| `-m, --map=MAP` | 只处理指定地图 |
| `-o, --output=FILE` | 输出到指定文件（默认 tmp.wad） |
| `-N, --no-nodes` | 不重建节点 |
| `-g, --gl` | 构建 GL 友好节点 |
| `-G, --gl-matching` | 构建与普通节点匹配的 GL 节点 |
| `-x, --gl-only` | 只构建 GL 节点 |
| `-z, --compress` | 压缩节点（含 GL 节点） |
| `-b, --empty-blockmap` | 生成空 blockmap |
| `-r, --empty-reject` | 生成空 reject 表 |
| `-w, --warn` | 显示警告信息 |
| `-V, --version` | 显示版本信息 |
| `--help` | 显示帮助 |

示例：

```bash
zdbsp -o nodes.wad map.wad     # 构建 BSP 节点
zdbsp -g -z map.wad -o gl.wad  # 构建压缩的 GL 节点
```

## 构建

- 构建系统：CMake（上游 `cmake_minimum_required 2.4`，适配补丁升至 3.5）
- 版本：1.19（上游 tag `v1.19`，2016-01-07）
- 许可证：GPL-2.0
- 源码：https://github.com/rheit/zdbsp/archive/refs/tags/v1.19.tar.gz
- 依赖：zlib/1.3.1（运行期唯一外部依赖）

## OHOS 适配

- 补丁 `0001-fix-cmake-zlib-target-ohos.patch`（4 处逻辑变更）：
  - `cmake_minimum_required` 2.4 → 3.5（CMake 4.x 兼容）
  - 系统 zlib 改用 `ZLIB::ZLIB` 导入目标（Conan CMakeDeps 语义）
  - 删除无条件覆盖 `ZDBSP_LIBS` 的旧变量行
  - `include_directories` 仅在内置 zlib 分支生效
- 64 位目标自动禁用 SSE（OHOS aarch64 无 SSE 代码路径）
- `stricmp/strnicmp` 缺失由 CMake 探测自动映射为 `strcasecmp/strncasecmp`
- 测试：test_package 在 HarmonyOS 上实机运行 zdbsp 处理最小 MAP01 WAD 验证节点构建（上游零测试，自建鸿蒙特有测试）
