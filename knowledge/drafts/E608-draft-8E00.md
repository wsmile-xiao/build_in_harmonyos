# E608 — meson i18n.merge_file 合并 polkit policy 需注入 GETTEXTDATADIR

## 错误特征
```
/storage/.../msgfmt: cannot locate ITS rules for ../accounts-service/com.endlessm.ParentalControls.policy.in
FAILED: [code=1] accounts-service/com.endlessm.ParentalControls.policy
```

## 触发条件
- 构建系统: meson（i18n.merge_file 处理 .policy/.xml）
- 阶段: compilation（ninja 执行 msgfmthelper）
- 软件含 polkit policy 文件（com.endlessm.ParentalControls.policy.in），依赖 conan polkit 包

## 根因分析
对 .policy（polkit 策略 XML）做 i18n.merge_file 翻译合并时，msgfmt 需要 gettext ITS 定位规则（polkit.its 定义可翻译节点、polkit.loc 定义 .policy 文件模式）。OHOS 工具链 msgfmt 的 ITS 数据目录（$HOME/usr/local/share/gettext/its）只含 fontconfig/gschema/gtk4builder 等通用规则，不含 polkit；而 conan polkit 包把 `polkit.its/polkit.loc` 装在包内 `share/gettext/its/`，不在 msgfmt 默认搜索路径。

## 解决方案

### 推荐方案
conanfile 构建环境注入 `GETTEXTDATADIR` 指向 polkit 依赖包的 `package_folder/share/gettext`（其下有 its/ 子目录），msgfmt 即从 `$GETTEXTDATADIR/its/` 读取 polkit.loc/polkit.its 完成翻译合并。
另一条路径：`configure_file(input:, output:, copy: true)` 直接安装英文 .policy 不合并翻译（accountsservice 0005 先例）——功能等价但丢失翻译，仅在 ITS 规则无法注入时兜底。

### 禁止做法
- ❌ 修改 usr/local 的 gettext ITS 目录（受保护环境目录）
- ❌ 忽略该目标继续构建（ninja 会停止，必须处理）

## 验证
```bash
# 修复前
ninja -C builddir com.endlessm.ParentalControls.policy
# msgfmt: cannot locate ITS rules ... FAILED code=1
# 修复后
GETTEXTDATADIR=/path/.conan2/p/polki.../p/share/gettext ninja -C builddir ...policy
# Merging translations ... policy 通过
```

## 适用与不适用边界
- 适用：meson 合并 polkit policy/XML 文件且依赖 conan polkit 包的项目（libmalcontent 0.10.2、同类 accounts-service 系）
- 不适用：无 i18n.merge_file 的项目；ITS 规则已装入工具链默认目录的环境

## 关联条目
- 相关（同软件族数据策略）: accountsservice 0005 patch（configure_file copy 兜底）