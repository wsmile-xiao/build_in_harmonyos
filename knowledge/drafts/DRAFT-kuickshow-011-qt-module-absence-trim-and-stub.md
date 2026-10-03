# DRAFT：OHOS qtbase 制品模块子集下的 Qt6/KF6 应用功能裁剪三步法

- **错误特征**：`Could NOT find Qt6PrintSupport` / `The following Qt components were not found: PrintSupport` / `Could not find a package configuration file provided by "KF6DocTools"`——上游 Qt6/KF6 应用在 ohpcd 制品闭包上 configure 阶段硬失败，但主库（qtbase/KF6 各包）明明在档。
- **根因**：ohpcd 的 qtbase/6.11.1 是固定模块子集（Core/Gui/Widgets/Network/Sql/Test/DBus/Concurrent/Xml），无 PrintSupport/UiPlugin/X11Extras 等；KF6 侧 kdoctools 不在发布闭包。上游按"Qt6 官方全发行版"假设写组件依赖，模块面不完整与库缺席是两类不同问题——前者应裁剪功能面保主体，后者才是断链。
- **解法（三步裁剪法，kuickshow 0.11.0 实证）**：
  1. 构建面摘除：组件表删缺席项 + 独占源/.ui 移出 + 子目录挂 `if(X_FOUND)` 守卫 + `CMAKE_DISABLE_FIND_PACKAGE_X=TRUE` 双保险；
  2. 动作面存根：不删动作注册（枚举键/快捷键配置依赖动作存在），只把槽函数体替换为 `KMessageBox::information("... not supported ...")`，冒烟路径零回归；
  3. 数据面补偿：被裁功能的数据制品仍随包安装，消费者测试按上游数据格式写契约断言（如 im_palette.pal 的 64 行十六进制三元组），验证从二进制扩展到数据形态。
- **降级方案**：缺席组件在应用主路径上被每次调用（非可选功能）时不可存根——依次尝试上游自带 disable 开关（kio USE_DBUS=OFF 先例）→ 提请补适配模块 → 判定不可做。
- **红线**：不要试图给 qtbase 私打补丁加模块（闭包锚点，一动全图 package_id 变化）；不要删上游动作/枚举定义（配置读写会崩）。
- **同族谱系**：kgoldrunner（单点 KIO 调用→等价 QDir API）、keditbookmarks（KF6::Parts 死路径删除）、knotifyconfig（.ui 控件级替换）——按"引用密度"分级处置：单点调用换 API / 死路径删 / 控件替换 / 功能存根。
