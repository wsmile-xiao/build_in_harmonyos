# dbf2mysql 1.14a 测试报告

## 环境与范围

- 目标平台：OpenHarmony PC aarch64（OHOS 6.0，Clang 15）
- 构建入口：Conan 2.29.1，`ci/conan/profiles/ohos-aarch64`
- 包类型：application；安装 `dbf2mysql`、`mysql2dbf` 两个命令行工具
- 上游构建系统：手写 Makefile
- 数据库依赖：`mariadb-connector-c/3.4.8`

## 上游测试基线

对解压后的 1.14a 原始源码检查顶层 Makefile、源码和目录结构，未发现
`test`/`check` 构建目标、测试目录或自动化测试入口。

| 口径 | 总数 N | 执行 N' | PASS | FAIL | SKIP | NOT_RUN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 上游自动化测试（断言） | 0 | 0 | 0 | 0 | 0 | 0 |

上游通过率记为 `0/0`（无测试入口），不把消费者测试混入上游分母。

## 适配后消费者测试

正式命令由 W3 在私有 `CONAN_HOME` 中执行：

```sh
conan create archives/d/dbf2mysql/1.14a \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

`test_package/test.sh` 在 Conan 生成的运行环境中执行以下 12 条断言：

| 分组 | 断言 | 结果 |
| --- | ---: | --- |
| 两个安装产物具有可执行权限 | 2 | 2/2 PASS |
| `dbf2mysql` 无参数退出码、版本和 usage | 3 | 3/3 PASS |
| `mysql2dbf` 无参数退出码、版本和 usage | 3 | 3/3 PASS |
| 缺失 DBF 输入的退出码和诊断 | 2 | 2/2 PASS |
| 不可创建 DBF 输出的退出码和诊断 | 2 | 2/2 PASS |
| **合计** | **12** | **12/12 PASS** |

| 口径 | 总数 | 执行 | PASS | FAIL | SKIP | NOT_RUN | 通过率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 新增消费者断言 | 12 | 12 | 12 | 0 | 0 | 0 | 12/12（100%） |
| 适配后合计（上游 + 新增） | 12 | 12 | 12 | 0 | 0 | 0 | 12/12（100%） |

## 构建与制品门禁

- `conan create` 完成从源码交叉构建、打包和 `test_package` 执行。
- 包内有两个 aarch64 ELF PIE 可执行文件；G4 产物完整性通过。
- L4：两个文件均为 NX enabled、PIE enabled、full RELRO。
- W3 本地 CI：退出码 0；消费者输出为 `[result] assertions passed: 12`。
- W5 知识图谱结构校验通过。

构建、打包、ELF 安全属性与知识图谱门禁不计入上述测试断言数量。

## 未覆盖场景

- 未连接真实 MySQL/MariaDB 服务执行 DBF→SQL 或 SQL→DBF 数据迁移；设备任务环境
  没有为该测试准备数据库服务、凭据和固定数据集。该联机场景记为功能验证
  `NOT_RUN`，不计入 12 条消费者断言的分母，也不声称已通过。
- 上游源码编译产生若干既有格式警告；本次补丁仅处理已移除的
  `mysql_connect` API，不扩大为上游代码清理。

## 证据

- 原始设备日志：`task-data/dbf2mysql-1.14a/logs/`（macOS 任务私有目录，不随 PR 提交）
- 设备 W3 原件：`archives/d/dbf2mysql/1.14a/reports/w3-local-ci.log`
- Conan 原始报告：`archives/d/dbf2mysql/1.14a/reports/conan-verify-report.{json,md}`
- 最终交付前以当前 HEAD 的重新验证回执和哈希为准；报告原件不作为手工放行依据。

## 结论

适配后两个命令行工具已在 OpenHarmony aarch64 上完成交叉构建和打包，消费者
12/12 通过。真实数据库联机迁移未执行，已单独披露。
