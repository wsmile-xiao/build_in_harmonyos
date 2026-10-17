# KtoBlzCheck

德国银行账号校验库（libktoblzcheck）+ 命令行工具（ktoblzcheck/ibanchk/benchmark）。

## 适配说明（1.53）

- CMake 构建，install 规则完整（库/头/工具/pkgconfig/cmake-config/bankdata）。
- `ENABLE_BANKDATA_DOWNLOAD=OFF`：默认 ON 会按当天日期联网下载银行数据
  （bundesbank.de），改为使用仓库自带 `src/bankdata/bankdata_20200420.txt`，
  install 后位于 `share/ktoblzcheck/`。
- python 绑定禁用：OHOS 无 Python 开发环境（交叉编译 python 扩展不可行）。
  补丁将 FindPython3 组件降为仅 Interpreter（避免 Development 缺失时 fallback
  到 REQUIRED Python2 导致 configure 失败），并跳过 `src/python` 子目录。
- 上游 ctest 含 4 个用例（ktoblzcheck/ibanchk_de/ibanchk_fr/benchmark），
  依赖仓库内 bankdata 文件；test_package 链接库调用 AccountNumberCheck API
  校验上游测试账号（20050550 @ 1262693334）。
