# conan 版本家族钉扎：在售低版本配方 + 全族 override 升钉统一家族

> 知识草稿（与 kjumpingcube 26.04.0 归档同 PR 交付）。
> Path: B（Curator 判定 A+B，配额 2/2）｜域: 依赖闭包｜等级: L2（次条）。
> 来源：kjumpingcube 26.04.0 适配，权威 CI attempt3 失败定位、attempt4 起 PASS。
> 同模式独立先例：libkdegames/26.04.0.1（karchive/6.18.0 override 钉扎，
> 解决 kiconthemes 要 6.19.0 与 knewstuff 要 6.18.0 的对撞）。

## 背景：制品仓版本离散

目标依赖家族（KF6）在制品仓（ohpcd）版本演进不同步：

| 包 | 在售版本 | 家族期望 |
|---|---|---|
| kxmlgui/kconfigwidgets/kcrash/kdbusaddons/kjobwidgets/kcolorscheme/kcompletion/kguiaddons/kitemviews/kwindowsystem/kauth/kbookmarks | 6.14.0 / **6.18.0** | 6.18.0 |
| karchive | 6.14.0 / **6.18.0** / 6.19.0 / 6.26.0 | 6.18.0 |
| kio | 6.14.0 / 6.26.0（**无 6.18.0**） | 6.18.0 家族 |
| solid | 6.14.0 / **6.18.0** / 6.26.0 | 6.18.0 |

kio 的版本选择是本条目的第一判据现场：6.26.0 不可选（其 recipe 要求
karchive/kconfig/kcoreaddons/ki18n/kservice/kcrash 全系 6.26，而
kconfigwidgets/kiconthemes 等没有 6.26.0 在售——整个 6.26 族闭包拼不齐），
只能取 6.14.0 并**向上**钉。

## 现象（阻塞面证据）

未做家族钉扎时，图解析直接失败：

```
ERROR: Version conflict: Conflict between kitemviews/6.18.0 and kitemviews/6.14.0 in the graph.
Conflict originates from kxmlgui/6.18.0
```

（kxmlgui/6.18.0 精确 require kitemviews/6.18.0，kio/6.14.0 精确 require
kitemviews/6.14.0——两个间接传递的精确版本在图里对撞，conan 不自动择优。）

## 根因与两阶段失败面

1. **图解析期**：conan 对同一包的多个精确版本声明报 Version conflict，
   不自动择优。
2. **配置期**（若绕过 (1)）：被消费包**已安装的 CMake config** 内嵌
   `find_dependency(KF6Xxx <构建时家族版本>)`。方向判据是本条目的核心：
   - 请求 `>= 6.14`、图内 6.18.0 → 满足（**升钉安全**）；
   - 请求 `>= 6.26`、图内 6.18.0 → configure 失败（**降钉不可行**）。
   KF6 大版本内 ABI 稳定是升钉可行的前提；跨大版本不得升钉。

## 修复：三步法

1. **选基础版本**：候选中取"在售且其传递闭包可被钉齐"的版本（判据 =
   对每个二级依赖问"升钉目标家族是否有售"）。
2. **全族 override**：消费方配方对该低版本配方钉扎的每个家族包显式
   `self.requires("<pkg>/<统一版本>", override=True)`。`override=True`
   语义是"整图强制此版本"，压过任意传递的精确声明。本例 18 个包升钉
   6.18.0（karchive/kauth/kbookmarks/kcolorscheme/kcompletion/kconfig/
   kconfigwidgets/kcoreaddons/kcrash/kguiaddons/ki18n/kiconthemes/
   kitemviews/kjobwidgets/kservice/kwidgetsaddons/kwindowsystem/solid）；
   仅被低版本配方独占、无对撞的传递依赖（如 libxml2/2.15.3）留在原版本。
3. **方向校验**：逐个核对被消费包已安装 configs 的 `find_dependency`
   版本请求均为 `>= 升钉前版本`。同模式先例 libkdegames/26.04.0.1 用
   单点 override（karchive/6.18.0）解决 6.19.0 vs 6.18.0 对撞，与本条
   是同一机理的轻量实例（对撞面 1 个包 vs 本例整族）。

## 关联判据（≥3 实例）

- 实例 1：kjumpingcube/26.04.0——18 处 `override=True` 家族升钉
  （kio/6.14.0 的 6.14 依赖族 → 6.18.0）；
- 实例 2：libkdegames/26.04.0.1——karchive/6.18.0 override（kiconthemes
  6.19 vs knewstuff 6.18 对撞）；
- 实例 3：kxmlgui/6.18.0 消费 karchive/6.19.0 制品（kiconthemes 传递），
  其 configs 按 `>= 6.18` 请求被 6.19/6.18 满足——同一"升钉方向安全"的
  消费面证据。

## 关联但正交的规则

R37（版本号占用）：制品仓不支持同版本多 revision 并存（409），配方内容
变更必须递增版本号后缀（26.04.0 → 26.04.0.1 即此规则的产物）。R37 管
"同版本 recipe 演进"，本条管"依赖家族版本离散"，正交。

## 验证（自包含）

1. 在不含 override 的消费者配方副本上 `conan graph info`（同 profile）
   应复现 `Version conflict`；
2. 补齐钉扎后重跑：无 Version conflict，二级家族包版本归一（对
   graph info 输出 grep 家族包名核对版本单一化）；
3. `grep -c "override=True" conanfile.py` 等于钉扎数（本例 18）；
4. `conan create --build=missing` 全图构建 + 权威 CI 通过。

## 查重差异（引用编号以 worktree 内 knowledge/graph 实际存在条目为准）

- 图谱检索 `override|版本冲突|pin|钉|version conflict`：仅 E480 提及
  传递消费（X11 头文件级依赖走 transitive_headers，免写桩 .pc），主题
  是"依赖可达性"而非"版本离散时的家族钉扎"；数据/词典类条目讲的是
  数据包固定版本与 hash 校验，与 conan 图版本对撞无关。
- 未命中任何以 conan Version conflict / 家族 override 升钉为主题的
  条目，新增。
