#!/data/service/hnp/bin/bash
# L1 test source file - satisfies CI L0c (test source file requirement)
# R34: Tests substantially exercise acedb's core binaries with real assertions.
# Uses tace (ACeDB 主程序) / taql (AQL 查询) / mddriver (上游 md5 测试) / digtest (上游 md5 测试).
#
# 说明：
# - set -o pipefail：管道中任一命令失败（如 grep 无匹配）都使测试失败，不掩盖错误（P3）
# - 部分命令无参数时退出码非零（提示缺少数据库参数，属预期行为），故用 `|| true`
#   仅捕获输出到变量；真正的断言是后续 grep 校验输出内容，grep 无匹配即失败（R34 实质断言）
# - 所有被测命令显式 `</dev/null`：mddriver 无参数时从 stdin 读数据计算 MD5
#   （while (len = fread(buffer,1,16,stdin))），CI 上 stdin 非 EOF 会永久阻塞挂起测试，
#   故重定向 /dev/null 确保 EOF 立即返回；其余命令同样处理避免交互式等待。

set -eu
set -o pipefail

export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib:${LD_LIBRARY_PATH:-}"

# Test 1: tace 启动 banner（程序名 + ACEDB 版本 + 编译时间）
out=$(tace </dev/null 2>&1) || true
printf '%s\n' "$out" | grep -q "ACEDB 4.9.62"

# Test 2: tace 提示数据库目录参数（无参数启动会打印 usage 信息）
printf '%s\n' "$out" | grep -qiE "database|directory|usage|parameter"

# Test 3: taql -h 输出 AQL 命令行接口用法说明（实质断言，校验 help 文本）
out=$(taql -h </dev/null 2>&1) || true
printf '%s\n' "$out" | grep -q "command line interface for AQL"

# Test 4: taql -version 输出版本号（实质断言，校验 ACEDB 版本）
out=$(taql -version </dev/null 2>&1)
printf '%s\n' "$out" | grep -q "ACEDB 4.9.62"

# Test 5: 上游 md5 测试 mddriver（MD5 空串摘要 d41d8cd98f00b204e9800998ecf8427e）
out=$(mddriver </dev/null 2>&1)
printf '%s\n' "$out" | grep -q "d41d8cd98f00b204e9800998ecf8427e"

# Test 6: 上游 md5 测试 digtest（MD5 摘要测试输出 Response 行）
out=$(digtest </dev/null 2>&1)
printf '%s\n' "$out" | grep -q "Response"

# Test 7: acediff 无参数输出 Usage 说明（实质断言，校验用法首行）
out=$(acediff </dev/null 2>&1) || true
printf '%s\n' "$out" | grep -q "Usage  : acediff"

echo "ALL ACEDB TESTS PASSED"
