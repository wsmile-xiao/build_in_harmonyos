# mysql-client-8.0 8.0.46 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMake 单仓，client-only + library-only 子集）
- 编译日期: 2026-09-12
- 编译器: OHOS clang（aarch64-linux-ohos，宿主鸿蒙 PC）
- 状态: built（本地 conan create 全绿；制品仓发布随 PR 合并后 CI 完成）
- 依赖（Conan 制品仓全部命中缓存二进制）: openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4、boost/1.84.0
- 参照: archives/m/mysql/8.0.46（同一源码同一补丁链的姊妹配方，已验证 published）+ knowledge E459

## 包定位与命名

- 包名 `mysql-client-8.0`：对齐 ConanCenter `libmysqlclient`（其前身为 mysql-client-8.0）
  的"纯客户端库"定位——只发 lib+include，不发客户端工具。
- 与姊妹包 `mysql/8.0.46` 的分工：`mysql` 提供 bin/ 下 20 个客户端工具 + 库；
  `mysql-client-8.0` 只提供 libmysqlclient.a + 头文件，供下游应用链接（如
  mydumper/qt-mysql 类消费者此前因无客户端库发布只能用 stub，本包补齐该缺口）。

## 版本选择

mysql-8.0 系列上游最新 GA：8.0.46（GitHub 官方仓 tag `mysql-8.0.46`）。发布 tarball 主源为官方 CDN（cdn.mysql.com，与 dev.mysql.com 同源），GitHub tag 归档为备源。
源码 sha256 = e0d1a98ae5188c6a4efed74c74ff28115d4b791bc9d591a78e14d20aded67344（与 archives/m/mysql/8.0.46 完全一致，官方 CDN tarball 实测校验）。

## 构建策略：复用已验证补丁链

本配方**零新增源码补丁**。15 个补丁全部复用 archives/m/mysql/8.0.46/patches/
（该配方经 PR !8023 合入 main、CI 绿、状态 published）——同一源码 tarball、
同一 OHOS 构建开关、同一 try_run 预置。差异仅在**打包边界**：

| 维度 | mysql/8.0.46（姊妹包） | mysql-client-8.0/8.0.46（本包） |
|---|---|---|
| 构建范围 | client-only（WITHOUT_SERVER=ON） | 相同 |
| bin/ 客户端工具 | 保留（mysql/mysqldump 等 20 个） | package() 阶段 rmdir 删除 |
| cpp_info.bindirs | ["bin"] | 不设置（library-only） |
| cmake_file_name | mysql | mysql_client_8.0（避免与 mysql 包 CONFIG 冲突） |
| cmake_target_name | mysql::mysql | mysql_client_8.0::mysqlclient |
| _validate_package | 断言 bin/mysql 等存在 | 断言 bin/ 不存在 + libmysqlclient.a 存在 |

构建图仍会编译 client 工具目标（client/CMakeLists 在 libmysql 之后），这是上游
单仓结构的固有依赖（工具链接 mysqlclient 库本身即是一次真实链接验证）；打包阶段
裁剪不影响库的正确性，且 test_package 从消费者视角二次验证。

## 编译步骤（本地 conan create）

1. 源码缓存：`~/tmp/builds/mysql-8.0.46.tar.gz`（sha256 与 conandata 一致时
   配方自动走本地缓存分支，跳过不可达的下载源）。
2. `conan create . mysql-client-8.0/8.0.46 -pr:h=~/.conan2/profiles/ohos-aarch64
   -pr:b=同 --build=missing`（后台 nohup，make -j6 约 6 分钟，峰值内存 ~2.5G）。
3. test_package：静态链接 test_mysql_client，69 用例（59 API + 10 OHOS 特有）全过。

## 配置迭代记录

无新增迭代——全部配置开关与 try_run 预置复用 mysql/8.0.46 已收敛结论
（该配方的 10 轮配置迭代记录见其 notes.md，此处不重复）。本配方开发中
实际遇到并解决的唯一问题是打包边界问题：

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | package() 后 bin/ 仍存在（首次 rmdir 未生效） | cmake.install() 后 bin/ 下还有 mysql_config 脚本与 20 个工具 | rmdir(package_folder/bin) 直接整体删除；_validate_package 增加"bin/ 必须不存在"断言防回归 |

## 编译期问题

无（复用已验证补丁链，15 个补丁覆盖的问题清单见 mysql/8.0.46 notes.md：
pthread_cancel 兜底 / DNS SRV 路径 / uchar 强转 / rpcgen 跳过 / comp_err 生成器 TARGET_FILE 化等）。

## 源码修改（patches/）

15 个补丁全部复制自 archives/m/mysql/8.0.46/patches/（内容逐字节一致），
补丁语义清单见同目录 conandata.yml 的 patch_description 字段。

## 测试

- test_package/test.c：69 用例（59 通用 API + 10 OHOS 特有），与 mysql/8.0.46
  同源（已验证），仅 CMakeLists.txt 的 find_package 目标名改为 mysql_client_8.0。
- 覆盖：客户端版本/初始化/字符集/转义/错误处理/SSL 选项/句柄生命周期/
  arm64 对齐/musl errno 隔离/静态链接完整性。

## 语言预检（R47）

C/C++ 项目（cpp 占比 84.3%+，与 mysql/8.0.46 同源码树；排除 bundled extra/
后为纯 C/C++ 项目，详见 mysql/8.0.46 notes.md 的预检记录）。

## 软件级元数据（并入本文件，PF9 路径闸要求变更全部落在版本目录内）

- **display**: MySQL 8.0 Client Library (libmysqlclient)
- **category**: db
- **定位**: `mysql-client-8.0` 是 MySQL 8.0 系列的 C 语言客户端库（libmysqlclient），**library-only 包**：只包含静态库 `lib/libmysqlclient.a` 与 `include/` 头文件，不包含客户端命令行工具（由姊妹包 `mysql` 提供）。命名与打包边界对齐 ConanCenter 的 `libmysqlclient` 配方风格。
- **下游价值**: mydumper/qt-mysql 类消费者此前因制品仓无独立客户端库包只能用 stub 方案（见 archives/m/mydumper notes），本包补齐该缺口。
- **依赖链**: openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4、boost/1.84.0（header-only）
