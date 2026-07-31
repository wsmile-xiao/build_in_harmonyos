# GNU datamash

GNU datamash 为表格数据提供统计、分组、转置、交叉表和文本转换操作。
本目录打包版本 1.9，并同时提供 `datamash` 与 `decorate` 两个命令。

## 使用示例

```bash
printf '1\n2\n3\n' | datamash sum 1
printf 'A\t1\nA\t2\nB\t5\n' | datamash -s -g 1 sum 2
printf 'C\nV\nIII\nIX\nXI\n' | decorate -k1,1:roman
```

## 适配说明

- 使用 GNU 官方源码和固定 SHA256。
- 使用 Conan 2 与 Autotools 构建。
- 配方执行上游完整 `make check`。
- `test_package` 从消费者视角运行打包后的两个命令。
- 未在本地冒充 OHOS AArch64 结果，最终平台结果以赛事 CI 为准。

## 链接

- 官网：https://www.gnu.org/software/datamash/
- 手册：https://www.gnu.org/software/datamash/manual/
- 源码：https://ftp.gnu.org/gnu/datamash/
