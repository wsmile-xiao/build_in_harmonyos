# boost1.84-locale

Boost.Locale 组件包（1.84.0）— 从 Boost 1.84.0 完整源码独立裁剪，std 后端 + musl 内置 iconv。

## 基本信息

- **名称**: boost1.84-locale
- **版本**: 1.84.0
- **主页**: https://www.boost.org/
- **许可证**: BSL-1.0
- **分类**: library (static)

## 鸿蒙适配要点

- b2 构建系统在 OHOS 不兼容（E068），手动编译 21 个源文件归档 libboost_locale.a
- 后端配置：std 后端启用，POSIX/WinAPI/ICU 后端禁用
- 编码转换：OHOS musl libc 内置 iconv（零新增依赖，上游 Linux 默认布局）
- 0001 补丁：smart_ptr sp_thread_sleep 跳过 pthread_setcancelstate（OHOS musl 无此函数）
- 测试二进制运行需 SDK libc++_shared.so（LD_LIBRARY_PATH 动态定位）+ ELF 自签名

## 已知限制（musl C 库数据差异，非适配缺陷）

- gbk 字符集 musl iconv 不支持
- sv_SE.UTF-8 / en_US.ISO8859-1 等 locale 数据 musl 未内置（libc++ 抛构造异常，上游测试守卫走跳过分支）
- iconv //TRANSLIT 不可用（glibc 专有），不可转换字符以 * 替换
- money_put 无千分位分组（musl mon_grouping 为空）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.84.0 | built | 首次适配（boost_1_84_0 官方源码） |
