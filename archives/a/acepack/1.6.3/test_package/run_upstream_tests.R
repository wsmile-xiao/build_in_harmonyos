# 上游测试 runner（base R 兼容层方案二：如实标注，不伪造）
# 用法: Rscript run_upstream_tests.R <test_package_dir>
# 说明: 用传入的 test_package 目录定位 mock-testthat.R 与 tests/ 下的
#       4 个上游测试文件，逐文件 source，输出 PASS/FAIL 汇总与 marker。
args <- commandArgs(trailingOnly = TRUE)
pkg_dir <- if (length(args) >= 1) args[1] else getwd()

options(warn = 1)
suppressPackageStartupMessages(source(file.path(pkg_dir, "mock-testthat.R")))
suppressPackageStartupMessages(library(acepack))

tdir <- file.path(pkg_dir, "tests")
files <- list.files(tdir, full.names = TRUE)
files <- files[grepl("^test_[A-Za-z_]+[.]R$", basename(files))]
for (f in files) {
  cat("== sourcing:", basename(f), "\n")
  source(f, echo = FALSE)
}

cat("\n===== 上游测试汇总（base R 兼容层）=====\n")
cat("PASS:", .env$pass, " FAIL:", .env$fail, "\n")
if (.env$fail > 0) {
  cat("失败明细:\n", paste(.env$failures, collapse = "\n"), "\n")
  cat("UPSTREAM_TESTS_VIA_COMPAT=FAIL_PARTIAL (", .env$pass, "/", (.env$pass + .env$fail), ")\n", sep = "")
} else {
  cat("UPSTREAM_TESTS_VIA_COMPAT=PASS (", .env$pass, "/", .env$pass, ")\n", sep = "")
}
# P1 修复：上游测试失败必须穿透到 CI 门禁（R9/R24），
# 按 .env$fail 返回非零退出码，使 run_test.sh 的 || 分支与 L1 门禁真实生效。
if (.env$fail > 0) quit(save = "no", status = 1) else quit(save = "no", status = 0)
