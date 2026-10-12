# boot 1.3-32 上游示例运行器（OHOS aarch64, R 4.5.1）
# ============================================================================
# 作用：运行上游 25 个含 \examples 的 man/*.Rd 中的全部示例代码。
#   - 用 tools::Rd2ex() 抽取每个 Rd 的示例代码块；
#   - 逐条（顶层表达式）tryCatch 执行，互不干扰地收集通过/失败；
#   - 所有绘图重定向到临时 pdf 设备（options(device=...)），禁止依赖 X11/X server；
#   - \dontrun{} 块（Rd2ex 输出为 "## Not run:" ... "## End(Not run)"）整体跳过；
#   - 打印 `EXAMPLES total=<n> passed=<n> failed=<n>` 与逐条失败摘要；
#   - 任一失败 → 非零退出码（R9/R24：上游失败必须穿透到门禁）。
#
# 用法: Rscript run_upstream_examples.R [boot_src_dir]
#   boot_src_dir: boot 源码树顶层（内含 man/）。缺省按 BOOT_SRC 环境变量、
#                 ./boot、$HOME/tmp/bootsrc/boot 顺序探测。
#   依赖: library(boot) 必须可用（由编排脚本装入临时库并经 R_LIBS 暴露）。
# ============================================================================
# 上游参照：tests/Examples/boot-Ex.Rout.save 含 915 条 "> " 输入行。
# ============================================================================

args <- commandArgs(trailingOnly = TRUE)

# ---- 定位源码树 -----------------------------------------------------------
resolve_src <- function() {
    if (length(args) >= 1L && nzchar(args[1L])) return(args[1L])
    env <- Sys.getenv("BOOT_SRC", unset = "")
    if (nzchar(env)) return(env)
    cand <- c(file.path(getwd(), "boot"),
              file.path(dirname(getwd()), "boot"),
              file.path(Sys.getenv("HOME"), "tmp", "bootsrc", "boot"))
    for (p in cand) if (dir.exists(p)) return(p)
    NA_character_
}

src_dir <- resolve_src()
if (is.na(src_dir) || !dir.exists(file.path(src_dir, "man"))) {
    cat("EXAMPLES_ERROR: 未找到 boot 源码树（需含 man/ 目录）\n")
    cat("  抽查路径: ", src_dir, "\n", sep = "")
    quit(save = "no", status = 2)
}
man_dir <- file.path(src_dir, "man")

# ---- 校验 boot 包可加载（R34：实质依赖被测包）-----------------------------
if (!requireNamespace("boot", quietly = TRUE)) {
    cat("EXAMPLES_ERROR: R 库树中不存在 boot 包（library(boot) 失败）\n")
    quit(save = "no", status = 2)
}
suppressPackageStartupMessages(library(boot))

# ---- 绘图重定向：默认设备写成临时 pdf，杜绝 X11 ---------------------------
# 每次新开图形设备都落到 TMPDIR 下的临时文件；不触碰任何 X server。
options(device = function(...) grDevices::pdf(file = tempfile(fileext = ".pdf")))
cat("EXAMPLES_DEVICE: options(device) -> pdf(tempfile()) [无 X11 依赖]\n")

# ---- 抽取辅助函数 ---------------------------------------------------------
# Rd2ex 的输出含头部注释块，示例代码从 "### ** Examples" 行之后开始。
extract_examples <- function(rd_file) {
    out <- tempfile(fileext = ".R")
    ok <- tryCatch(tools::Rd2ex(rd_file, out), error = function(e) FALSE)
    if (!isTRUE(ok) && !file.exists(out)) return(NULL)
    if (!file.exists(out)) return(NULL)
    L <- readLines(out, warn = FALSE)
    idx <- grep("^### \\*\\* Examples", L)
    if (!length(idx)) return(NULL)
    code <- L[-seq_len(idx[1L])]
    drop_dontrun(code)
}

# 去掉 \dontrun{} 块：Rd2ex 会写成 "## Not run:" ... "## End(Not run)"
drop_dontrun <- function(code) {
    out <- character(0L)
    skip <- FALSE
    for (ln in code) {
        if (grepl("^## Not run:", ln)) { skip <- TRUE;  next }
        if (grepl("^## End\\(Not run\\)", ln)) { skip <- FALSE; next }
        if (!skip) out <- c(out, ln)
    }
    out
}

# ---- 遍历 man/*.Rd --------------------------------------------------------
rd_files <- sort(list.files(man_dir, pattern = "\\.Rd$", full.names = TRUE))
total <- 0L; passed <- 0L; failed <- 0L
failures <- character(0L)
per_file <- list()

for (rd in rd_files) {
    fname <- basename(rd)
    code <- extract_examples(rd)
    if (is.null(code)) next                       # 该 Rd 无示例，跳过
    exprs <- tryCatch(parse(text = code), error = function(e) e)
    if (inherits(exprs, "error")) {
        # 整体解析失败：计 1 条失败，附文件级诊断
        total <- total + 1L; failed <- failed + 1L
        msg <- paste0("parse error: ", conditionMessage(exprs))
        failures <- c(failures, paste0(fname, " [whole-file] ", msg))
        per_file[[fname]] <- c(total = 1L, pass = 0L, fail = 1L)
        next
    }
    n_expr <- length(exprs)
    if (n_expr == 0L) next
    # 每个 Rd 一个独立执行环境（与 R CMD check 按文件隔离一致），
    # 父环境为 globalenv，使 library(boot) 的导出与数据集可见。
    env <- new.env(parent = globalenv())
    # 固定种子：部分上游示例使用 rexp()/随机重抽样（如 lines.saddle.distn.Rd
    # 用 rexp(12) 且无 set.seed），需固定 RNG 才能可复现（seed 1 已实测通过）。
    set.seed(1L)
    fpass <- 0L; ffail <- 0L
    for (k in seq_len(n_expr)) {
        e <- exprs[[k]]
        err <- tryCatch({
            suppressMessages(utils::capture.output(eval(e, envir = env)))
            NULL
        }, error = function(er) er)
        total <- total + 1L
        if (is.null(err)) {
            passed <- passed + 1L; fpass <- fpass + 1L
        } else {
            failed <- failed + 1L; ffail <- ffail + 1L
            elab <- paste(deparse(e, width.cutoff = 60L)[1L], collapse = " ")
            if (nchar(elab) > 70L) elab <- paste0(substr(elab, 1L, 67L), "...")
            failures <- c(failures, sprintf("%s [#%d] %s  => %s",
                                            fname, k, elab,
                                            conditionMessage(err)))
        }
    }
    per_file[[fname]] <- c(total = n_expr, pass = fpass, fail = ffail)
    graphics.off()
}

# ---- 逐文件小结 -----------------------------------------------------------
cat("\n===== 上游示例逐文件小结 =====\n")
for (nm in names(per_file)) {
    v <- per_file[[nm]]
    cat(sprintf("  %-24s total=%-3d pass=%-3d fail=%d\n",
                nm, v[["total"]], v[["pass"]], v[["fail"]]))
}

# ---- 与上游 Ex.Rout.save 的 "> " 行数对照（总量参照）----------------------
ref_file <- file.path(src_dir, "tests", "Examples", "boot-Ex.Rout.save")
ref_n <- NA_integer_
if (file.exists(ref_file)) {
    ref_n <- sum(grepl("^> ", readLines(ref_file, warn = FALSE)))
}
if (!is.na(ref_n)) {
    cat(sprintf("EXAMPLES_REFERENCE: 上游 boot-Ex.Rout.save 含 %d 条 '> ' 输入行（参照）\n",
                ref_n))
}

# ---- 失败明细 -------------------------------------------------------------
if (failed > 0L) {
    cat("\n===== 失败明细 =====\n")
    cat(paste0("  ", failures, collapse = "\n"), "\n", sep = "")
}

cat(sprintf("\nEXAMPLES total=%d passed=%d failed=%d\n", total, passed, failed))
if (failed > 0L) quit(save = "no", status = 1L) else quit(save = "no", status = 0L)
