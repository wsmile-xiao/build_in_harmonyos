// cli_smoke.js — mujs CLI 端到端冒烟（R38/L0k 验证）
// 运行：mujs test_package/cli_smoke.js；退出码 0 且输出 ok 即通过
var a = [1, 2, 3].map(function (x) { return x * 2; });
if (a.join(",") !== "2,4,6") {
    throw new Error("mujs CLI smoke failed");
}
print("mujs CLI smoke ok");
