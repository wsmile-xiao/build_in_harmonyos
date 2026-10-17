# SKILL 执行流程反馈报告 — ttylog/0.31

## 背景
- 软件/版本：ttylog 0.31；上游仓库：https://git.code.sf.net/p/ttylog/code
- 构建系统：CMake（源码根目录 CMakeLists.txt）；依赖：系统 libc；补丁：0；适配路径：路径 A，静态 OHOS CLI。
- 作者：lkjing2021345 <1908499668@qq.com>；日期：2026-09-24。

## 情况
| 阶段 | 结果 |
|---|---|
| init-build | 官方 Git URL 被当作压缩包访问产生 404；改用同项目官方 0.31 tarball；启发式将实际 CMake 错判 autotools。 |
| 交叉编译 | NDK clang 15.0.4 成功；动态可执行缺 OHOS loader，使用同源目标文件静态重链后 QEMU 上游 2/2 项通过。 |
| conan-verify | G1 首轮因未声明无补丁导出/应用钩子失败（仓库已有 E429 草稿）；G2 首轮因 `/download` URL 被错识别为 zip 报 BadZipFile（E483）。修正后 G1/G2/G3 通过，交付 CLI 经 qemu 4/4 通过。 |
| finish / W3 | setup.sh 与 build_and_test.sh 均通过；历史旧 G0 仍用不存在的 configure 作非阻断探针；废弃 packaging 预检提示、SUMMARY 生成异常，未将它们误报为 W3 失败。 |
| PR / 机器人 / 远程 CI | 首次 PR 前形成此终稿；机器人检视与远程 CI 尚未发生，等待用户主动复查。 |

### 失败分析及知识图谱
- 使用 E483 解决 SourceForge 下载格式误识别；已有 E429 草稿涵盖无补丁 G1 钩子，避免重复新增。
- 新增 E585 草稿记录“init-build 将含 CMakeLists.txt 的项目判为 autotools，conan-init 继承错判”；draft-review 判定 create，最近 E232 相似度 0.19；graph validate 通过（存量警告不属本 PR）。
- 上游 2/2 项 QEMU 通过；交付产物 test_package 4/4 QEMU 通过。物理串口采集未测试（runner 无 OHOS 串口设备）；没有伪报动态产物实跑。
- HANDOFF：0 个阻断性 W3；修复尝试：G1 一轮，G2 一轮。主要瓶颈：源码构建系统误判和旧 G0 清洁构建探针。

### AI 检视与 CI
- PR 尚未建立，变更摘要/检视意见/远程 CI 均待异步产生；本地 W3 已通过，不提前声称远程绿。

## 建议
### SKILL 设计改进
- `scripts/ohc/init_build.py:428` 在取得源码后用顶层真实构建入口复核按 URL 猜测的 `build_system`；`scripts/ohc/conan_recipe.py:145-160` 如已探测到 CMakeLists.txt，应提示与 manifest 值冲突，而不是直接采用 autotools。这样首次配方不会错误调用 configure。

### 模板改进
- `scripts/ohc/conan_recipe.py:215-217` 选择模板时增加 CMake-only CLI 示例；初稿 `conanfile.py` 用的 Autotools 模板不仅把可执行文件标为 library，还把 license 写成 MIT、源码键写成无版本平铺。生成后必须人工纠正，建议用 `package_type=application` + `bin/` + 版本键官方 SHA 的骨架。

### 自动化补全
- `scripts/ohc/finish.py:365-385` 的 readiness 对 v2 已废弃的 `packaging/` 仍报告缺失，应根据 W3 Conan 产物判定；旧 G0 按错误的 autotools context 调用 configure，应从配方或语言预检结果识别 CMake。反馈自动骨架还把构建系统保留 `{BUILD_SYSTEM}`、上游标“未知”、测试统计记 0，生成时应读取 conandata/manifest 与 W3 日志。

### 知识图谱覆盖
- `knowledge/drafts/E585-draft-50E3.kv` 与配套 `.md` 提供 init-build/conan-init 构建系统错判的诊断和修正命令，建议主编审核后 promote；SourceForge 解包及无补丁 G1 已由 E483/E429 覆盖，不重复造条目。

## 作者
- 姓名：lkjing2021345
- 邮箱：1908499668@qq.com
- 草稿：E585-draft-50E3；PR：提交后由远程自动关联，本文在首次建 PR 前已闭环。
