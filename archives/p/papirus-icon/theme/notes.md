# papirus-icon/theme 适配笔记

## 编译环境
- 构建系统: makefile (all: 为空，纯资源复制)
- 编译日期: 2026-07-28
- 编译器: N/A (无编译步骤)
- 状态: built

## 编译步骤

papirus-icon-theme 是纯图标主题资源包，无需编译。Conan recipe 的 build() 为 pass。
package() 直接将 Papirus/Papirus-Dark/Papirus-Light 复制到 package_folder/share/icons/。

## 上游 Makefile

- `make all`：空 target
- `make install`：复制 ICON_THEMES 到 DESTDIR/PREFIX/share/icons/
- `make test_short`：7 个短校验 target
- `make test-all`：8 个校验 target（含 test_xml_struct 依赖 xmlstarlet）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_symlinks 失败 | 上游源码存在 BROKEN=306 app alias 断链 + CASE=276 大小写别名 | 分类验证（PASS/CASE/BROKEN/LOOP），上游既有不阻塞 |
| 2 | test_xml_struct 不可执行 | 缺 xmlstarlet | 记录为未执行；test_package 用 Python XML 做替代验证 |
| 3 | conan source() 符号链接循环 | get() 默认 tarfile 提取遇到 Errno 40 | tarfile.open(errorlevel=0) + extractall(filter="data") |

## 上游测试结果

| Target | 结果 | 说明 |
|--------|------|------|
| test_rendering_glitches | PASS | |
| test_optimization | PASS | |
| test_svg_elems | PASS | |
| test_symlinks | FAIL | BROKEN=306, CASE=276, LOOP=0; 均为上游既有 |
| test_filenames | PASS | |
| test_decimal_size | PASS | |
| test_lengths_units | PASS | |
| test_xml_struct | 未执行 | 缺 xmlstarlet |

Short: 6/7 PASS, test-all: 7/8 已执行

## 依赖状态
- 无第三方 Conan 前置依赖（图标主题资源型叶子库）
- 可选验证工具仅记录，不混入 PR

## 安装路径
- share/icons/Papirus/
- share/icons/Papirus-Dark/
- share/icons/Papirus-Light/
- share/icons/LICENSE / AUTHORS

## 统计
| 类别 | 数量 |
|------|------|
| 主题目录数 | 116 |
| SVG | 50,596 |
| PNG | 1 |
| Symlinks 总数 | 50,271 |
| BROKEN | 306 (apps alias, 上游既有) |
| CASE | 276 (大小写别名) |
| LOOP | 0 |

---

**编译结束**: 2026-07-28
**最终状态**: built
