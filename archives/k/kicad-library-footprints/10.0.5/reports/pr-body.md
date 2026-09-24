- **三方库名称**：kicad-library-footprints
- **上游版本**：10.0.5
- **上游仓库地址**：https://gitlab.com/kicad/libraries/kicad-footprints
- **适配路径**：路径 A（基础适配）
- **使用知识库**：build_in_harmonyos 根目录 `SKILL.md`、资源型 CMake 包规范、KiCad 资源包案例

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 源码归档无 `tests/`、pytest 或单元测试注册 |
| 集成测试 | 0 | 无 `enable_testing()`、`add_test()` 或 CTest |
| 其他测试 | 0 | `.gitlab-ci.yml` 远程 include `kicad-library-utils`，检查脚本不随源码归档提供 |
| **合计** | **0** | 上游未提供可在 Conan 包内直接运行的测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 15,454 | +15,454 | 资源布局、许可证、库表、155 个库目录和 15,447 个 footprint 文件结构断言 |
| 集成测试 | 1 | +1 | 截断 footprint 负向消费测试 |
| 鸿蒙特有测试 | 2 | 新增 | `--ohos` 下 `TMPDIR` 存在且避开只读 `/tmp` |
| **合计** | **15,456** | **+15,456** | 鸿蒙模式实际通过 15,456/15,456 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

补全范围是 Conan consumer 对安装后 KiCad 资源布局和文件完整性的验证。原因是上游 footprint 仓库本身只有资源安装工程，CI 检查脚本通过另一个仓库远程 include，不能作为本包的稳定测试依赖。新增文件：

1. `test_package/test_kicad_footprints.py` — 资源布局、库表映射、全部 footprint s-expression、截断负向和 OHOS TMPDIR 测试。
2. `test_package/conanfile.py` — 真实声明依赖被测包并调用消费者脚本。
3. `test_package/MANIFEST.yml` — 测试入口、上游测试缺失说明和断言计数。

## 验证结果

- 编译状态：通过（上游为 `project(... NONE)`，CMake 配置/构建/安装/打包真实成功；无 C/C++ 编译单元）
- 上游测试用例通过率：N/A（0 个可执行上游测试）
- 新增测试用例通过率：15,456/15,456（100%）
- 空包负向验证：按预期失败，退出码 1
- OHOS profile：本机 Windows 因 `/data/service/hnp/bin/bash`/Unix Makefiles 不可执行而未完成；不是 HarmonyOS worker 通过结果

## 补充说明

包内容使用上游官方 tarball，SHA-256 为 `f6305041ea72ab9c55461873dfd67359d28fa9639e7a11952b81d468b2155a8d`，无补丁、无运行时依赖。用户提供的 HarmonyOS 6.0 真机 `10.53.45.8:8022` 在本次任务中 TCP/ICMP 均超时，因此未虚构设备端结果；设备恢复可达后应按 `notes.md` 的 OHOS profile 命令补跑。
