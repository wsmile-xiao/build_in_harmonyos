# cotila 1.2.1 适配笔记

## 选型与版本核验（2026-09-07）

- GitHub calebzulawski/cotila tags 实拉：`1.2.1`（**无 v 前缀**，v1.2.1 不存在）
  ——sourceUrl 指向官方 tag archive，sha256 实测锚定 ✓
- 档案无 cotila；制品仓零发布（R35：conan list 交叉确认）✓
- 平台任务 contrib-6597 已认领（claimer Ember5843，Agent 代领第一单）✓

## 库形态与配方决策

- **header-only**：`include/cotila/**` 全头文件 + CMake INTERFACE target
  （`cotila::cotila`），install(DIRECTORY) 装头文件 → 配方无 build 阶段，
  package 直接拷头文件树（模板 conanfile-headeronly.py.tmpl，变体 A）
- 无可执行/动态库产物 → **E549 签名不适用**（无 ELF 产物）
- C++17 起步：validate 里 check_min_cppstd(17)
- 上游测试 = doctest via CMake FetchContent（需联网拉 doctest）→ 配方不跑
  上游测试（R51 如实申报），R34 由 test_package 承担：constexpr
  static_assert（dot/trace 编译期）+ 运行期断言双保险

## test_package 设计

- `cotila::make_vector(1,2,3)` dot 自积 = 14（编译期 static_assert）
- `cotila::matrix<double,2,2>{{{1,2},{3,4}}}` trace = 5（编译期 + 运行期）
- CMake 消费者工程：find_package(cotila) + cotila::cotila，CXX_STANDARD 17，
  OHOS 下 CMAKE_SYSTEM_NAME=Linux + -stdlib=libc++（rang 先例模式）

## 待办（Phase 2，设备侧）

- [ ] bundle 推送 → conan create → conan-verify 八门禁修复循环 → finish

## 对话记录（关键转折）

- 2026-09-07 用户授权 Agent 代为认领（账号 Ember5843）→ 六连筛全绿后浏览器两段式确认领取
  contrib-6597（10 火种），API 终验 assigned
- 首轮 create：conan 2 硬校验 package_type=library 缺 shared option → 改 header-library（先例 rang）
- conan-verify G1：header-only 模板"无 build()"不合规 → 补空 build() + apply_conandata_patches
  （不伪造编译日志）；L0e 缺 test_package/MANIFEST.yml → 补上游测试声明
- finish JC6：设备克隆 origin/main 指旧离线包 → update-ref 修正基线（AGENTS.md 已知坑）后全绿

## 终态（2026-09-07）

- **status: built（submit 就绪）**：conan create + test_package 实跑（dot=14 trace=5）+
  八门禁 + W3/W2 全绿；成功路径沉淀为 header-only 库标杆先例
- 下一步（人工）：push 分支 → submit 建 PR → CI 绿后 submit 自动升级 success（R50）

---

**编译结束**: 2026-09-08 11:30
**最终状态**: built
