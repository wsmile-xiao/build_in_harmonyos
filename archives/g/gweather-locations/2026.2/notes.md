# gweather-locations 2026.2 适配笔记

## 包定位

GNOME 数据模块（无 C/C++ 编译产物）：meson 构建期用 python3 + PyGObject 跑
`build-aux/gen_locations_variant.py`，把 `data/Locations.xml` 转成
`libdir/gweather-locations/Locations.bin`（magic `GWthDB01`，GVariant
normal form，host-endian）。`gweather-locations.pc` 输出 `locations_db` /
`locations_xml` / `locations_dtd` 变量；libgweather-4 顶层 meson 以
`dependency('gweather-locations')` + `locations_db` 消费（编译期注入
`GWEATHER_LOCATIONS_DB`，运行期可用 `LIBGWEATHER_LOCATIONS_PATH` 覆盖）。

## 核心适配：PyGObject 缺失 → 纯 python gi shim

上游生成器只用 `gi.repository.GLib` 构造 `GLib.Variant`（构造 + 
`get_data_as_bytes`），不涉及主循环/类型仓库。方案：recipe 自带 `shim/gi/`
纯 python 包，实现该生成器用到的 GVariant 序列化子集（y b n q i u x t d s
基本类型、tuple、dict entry、array、嵌套 Variant 嵌入），`PYTHONPATH` 同时
注入 meson 的 `find_installation('python3', modules: ['gi'])` 探测与 ninja
执行生成器的子进程。生成器在 little-endian 主机上的 byteswap 分支是死代码
（上游注释），与 shim 的小端实现一致。

### shim 的关键正确性点（踩坑实录）

1. **tuple framing offsets 必须逆子顺序**：GVariant 规范里 tuple/dict entry
   的 framing offsets 按子顺序逆序追加到容器尾（第一个非末子元素的 offset
   最靠近容器尾字节）；array 则是正序、每元素一个（含末元素）。早期 shim
   用正序，产出的 Locations.bin 能过 magic 校验、大小也对，但 libgweather
   一解析就崩（TAP 报 start<=end 断言）——这是修复版 shim 的由来。修复后
   产物与设备上真 GLib（PyGObject twin 实验）逐字节一致。
2. **offset 字宽由容器序列化后总大小决定**：<=255:1B、<=65535:2B、
   <=2^32-1:4B、其余 8B（两端逻辑必须对称）。
3. **嵌套 Variant**：生成器把 `(ss)` 风牌子 Variant 直接嵌进父 Variant，
   shim 需按"类型串完全一致即放行"实现 PyGObject 的嵌入语义。

## 构建环境注入

- `NINJA` 绝对路径：OHOS musl python 的子进程解析不了 hnp 裸名符号链接，
  ninja 必须以绝对路径注入（geocode-glib 3.26.4 先例）。
- `LD_LIBRARY_PATH=/system/lib64`：meson python 探测需要 libc++_shared.so。
- 无需任何 C 编译开关；`-Dintrospection` 之类选项本项目不存在。

## 上游测试

tarball 无 tests/ 目录、无功能测试；`data/meson.build` 仅条件注册 2 个
lint 项（均 `required: false`）：
- `Valid Locations file`：xmllint `--valid` 校验 Locations.xml 符合随包
  locations.dtd —— xmllint 在 PATH 时注册，OHOS 环境实测注册并 1/1 OK；
  recipe 在 `build()` 内 `Meson(self).test()` 真实执行，CI 日志可证。
- pylint 风格检查：pylint 未安装，不注册。

因此本包不适用 NO_UPSTREAM_TESTS 免除：上游 lint 套件真实执行，另有
test_package 的消费者级全量解析作为补充执行证据。

## test_package（消费者验证）

数据型包无头文件/库，无 CMake 可编译目标（CMakeDeps 对无 include/ 的数据
包会生成坏 target，libgweather-4 run 已实证），故 test_package 不带
CMakeLists.txt（对规范的最小偏离，理由如上）：

1. `conanfile.py`：守卫安装面完整性（Locations.bin / Locations.xml /
   locations.dtd / gweather-locations.pc 存在，pc 含 locations_db、
   locations_xml 变量），随后以设备 python3 跑 `test_locations.py`。
2. `test_locations.py`：纯 python GVariant 反序列化器，全量解析
   Locations.bin 并校验：magic、顶层 5 成员结构、规模下界（locations/
   timezones/countries/METAR）、全部 children/parent/nearest/tz-hint/
   zones 索引界内（坏序列化最先炸的点）、Europe/Paris、America/New_York、
   Paris 城市、London/Tokyo 条目、LFPG 台站。实测 17 项全过（642680 字节，
   locations=8862、timezones=332、countries=245、metar=4004）。

## 与 libgweather-4 的协同

本包是 libgweather-4 4.6.0 依赖闭包（R36）的一环：libgweather meson 消费
本包 pc 的 `locations_db` 变量取 Locations.bin；其 TAP 测试套件（含
timezones 全量遍历）已在本包修复版产物上全绿。本包单独交付并发布后，
libgweather-4 run 的权威 CI L0i 即可解除。
