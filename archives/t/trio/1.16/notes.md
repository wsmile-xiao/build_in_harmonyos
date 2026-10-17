# trio 1.16 — HarmonyOS PC 适配记录

## 基本信息
- 软件：trio（可移植的 printf/sprintf/scanf 替换库）
- 版本：1.16
- 上游：https://sourceforge.net/projects/ctrio/
- 构建系统：autotools（发布包自带预生成 configure）

## 适配要点
1. **HMDFS umask**：configure 以 `umask 077` 创建临时目录，HMDFS 上目录权限
   异常（drwx--S---），config.status 读取 subs1.awk 时 Permission denied；
   补丁改为 `umask 022`。
2. **noexec 构建目录**：config.status 用 `awk -f script` 执行替换程序时，
   awk 需要对脚本做 mmap 而失败；补丁改为把替换程序经 stdin 传入
   （`awk -f - < subs.awk`），sed 输出先落盘到 $TMPDIR 下的临时文件。
3. **build triplet**：OHOS 下显式 `--build=aarch64-unknown-linux-gnu`，
   避免 config.guess 在 noexec 目录编译探测程序失败。
4. **ar/ranlib**：OHOS 工具链 PATH 无裸 ar/ranlib，通过环境变量指向
   llvm-ar/llvm-ranlib。
5. **静态库**：默认只构建并安装 libtrio.a，不装 .so。

## 验证
- WSL 本地 `conan create` 通过（OHOS 模拟 settings）。
- 官方流水线 L0/L1/L4/L5。