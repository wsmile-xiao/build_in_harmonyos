# boot 1.3-32 上游测试运行器（OHOS aarch64, R 4.5.1）
# ============================================================================
# 作用：
#   1) 确保 Suggests 依赖 survival / MASS 可用；缺失则从 CRAN 源码包
#      （tuna 镜像）R CMD INSTALL 到临时库（含 Matrix/lattice 依赖链）。
#      编译器导出 CC/CXX/AR/RANLIB 指向 /data/service/hnp/bin/*（R33：取自
#      显式路径，不用裸 shell 变量）。
#   2) 真实运行上游 tests/parallel-censboot.R：它 library(survival) 且用
#      parallel="multicore", ncpus=2。装成功就真跑并给出 PASS/FAIL；
#      装不上或缺能力（如 OHOS 禁 fork → multicore 失败）则输出
#      `SKIPPED: <原因+证据命令>`，绝不伪造通过。
#   3) 对 50 个 data/*.rda 做可 load 校验，并与 man/ 数据文档交叉核对。
#
# 用法: Rscript run_upstream_tests.R [boot_src_dir]
#   环境: R_LIBS     指向含 boot（及 survival/MASS）的库树
#         BOOT_DEP_CACHE 预置依赖 tarball 的缓存目录（可选，缺省再联网下载）
# ============================================================================

args <- commandArgs(trailingOnly = TRUE)

resolve_src <- function() {
    if (length(args) >= 1L && nzchar(args[1L])) return(args[1L])
    env <- Sys.getenv("BOOT_SRC", unset = "")
    if (nzchar(env)) return(env)
    cand <- c(file.path(getwd(), "boot"),
              file.path(Sys.getenv("HOME"), "tmp", "bootsrc", "boot"))
    for (p in cand) if (dir.exists(p)) return(p)
    NA_character_
}
src_dir <- resolve_src()
if (is.na(src_dir) || !file.exists(file.path(src_dir, "DESCRIPTION"))) {
    cat("UPSTREAM_TESTS ERROR: 未找到 boot 源码树\n")
    quit(save = "no", status = 2)
}

mirror <- Sys.getenv("BOOT_CRAN_MIRROR",
                     "https://mirrors.tuna.tsinghua.edu.cn/CRAN/src/contrib")
dep_cache <- Sys.getenv("BOOT_DEP_CACHE", file.path(tempdir(), "boot-dep-cache"))
if (!dir.exists(dep_cache)) dir.create(dep_cache, recursive = TRUE, showWarnings = FALSE)
lib <- .libPaths()[1L]

# ---- 编译器环境（R33：显式路径，不依赖裸 shell 变量）----------------------
hnp <- "/data/service/hnp/bin"
pick <- function(env, def) { v <- Sys.getenv(env, ""); if (nzchar(v)) v else def }
cc  <- pick("CC",  file.path(hnp, "clang"))
cxx <- pick("CXX", file.path(hnp, "clang++"))
ar  <- pick("AR",  file.path(hnp, "llvm-ar"))
ran <- pick("RANLIB", file.path(hnp, "llvm-ranlib"))
if (file.exists(cc))  Sys.setenv(CC = cc)
if (file.exists(cxx)) Sys.setenv(CXX = cxx)
if (file.exists(ar))  Sys.setenv(AR = ar)
if (file.exists(ran)) Sys.setenv(RANLIB = ran)
rbin <- file.path(R.home("bin"), "R")

# ---- 依赖安装：从缓存/镜像取源码包并编译安装 ------------------------------
find_tarball <- function(pkg) {
    hit <- list.files(dep_cache, pattern = paste0("^", pkg, "_.*\\.tar\\.gz$"),
                      full.names = TRUE)
    if (length(hit)) return(hit[1L])
    NA_character_
}

cran_version <- function(pkg) {
    idx <- file.path(dep_cache, "PACKAGES")
    if (!file.exists(idx)) {
        ok <- tryCatch({ utils::download.file(file.path(mirror, "PACKAGES"), idx,
                                              quiet = TRUE, mode = "wb"); TRUE },
                       error = function(e) FALSE, warning = function(w) FALSE)
        if (!isTRUE(ok)) return(NA_character_)
    }
    L <- tryCatch(readLines(idx, warn = FALSE), error = function(e) character(0))
    i <- grep(paste0("^Package: ", pkg, "$"), L)
    if (!length(i)) return(NA_character_)
    v <- grep("^Version:", L[(i[1L]):min(i[1L] + 30L, length(L))], value = TRUE)
    if (!length(v)) return(NA_character_)
    sub("^Version:\\s*", "", v[1L])
}

ensure_dep <- function(pkg) {
    if (requireNamespace(pkg, quietly = TRUE)) return(list(ok = TRUE, how = "已经可用"))
    tb <- find_tarball(pkg)
    if (is.na(tb)) {
        ver <- cran_version(pkg)
        if (is.na(ver)) return(list(ok = FALSE, how = paste0(
            "无法获取 ", pkg, " 版本（镜像不可达: ", mirror, "）")))
        tb <- file.path(dep_cache, paste0(pkg, "_", ver, ".tar.gz"))
        ok <- tryCatch({ utils::download.file(
            file.path(mirror, paste0(pkg, "_", ver, ".tar.gz")), tb,
            quiet = TRUE, mode = "wb"); TRUE }, error = function(e) FALSE,
            warning = function(w) FALSE)
        if (!isTRUE(ok) || !file.exists(tb))
            return(list(ok = FALSE, how = paste0("下载失败: ", tb)))
    }
    logf <- file.path(dep_cache, paste0("install-", pkg, ".log"))
    rc <- suppressWarnings(system2(rbin, c("CMD", "INSTALL",
              paste0("--library=", lib), shQuote(tb)),
              stdout = logf, stderr = logf))
    ok <- (rc == 0L) && requireNamespace(pkg, quietly = TRUE)
    list(ok = ok, how = if (ok) paste0("已编译安装 (", basename(tb), ")") else
        paste0("安装失败 rc=", rc, " 详见 ", logf))
}

# 依赖链顺序：lattice -> Matrix -> survival；MASS 独立
dep_specs <- c("lattice", "Matrix", "survival", "MASS")
dep_status <- list()
for (p in dep_specs) dep_status[[p]] <- ensure_dep(p)

cat("===== Suggests 依赖状态 =====\n")
for (p in dep_specs) {
    cat(sprintf("  %-9s : %s (%s)\n", p, if (dep_status[[p]]$ok) "OK" else "MISSING",
                dep_status[[p]]$how))
}

have_survival <- isTRUE(dep_status[["survival"]]$ok)
have_mass     <- isTRUE(dep_status[["MASS"]]$ok)

# ==========================================================================
# 步骤 2：运行上游 tests/parallel-censboot.R
# ==========================================================================
test_file <- file.path(src_dir, "tests", "parallel-censboot.R")
cat("\n===== 上游测试: tests/parallel-censboot.R =====\n")
cat("  源文件存在:", file.exists(test_file), " survival 可用:", have_survival, "\n")

upstream_result <- "FAIL"
upstream_detail <- ""

if (!file.exists(test_file)) {
    upstream_result <- "SKIPPED"
    upstream_detail <- paste0("上游测试文件缺失: ", test_file)
} else if (!have_survival) {
    upstream_result <- "SKIPPED"
    upstream_detail <- paste0(
        "survival 不可用（", dep_status[["survival"]]$how,
        "）；证据命令: Rscript -e 'library(survival)'  ->  there is no package called 'survival'")
} else {
    # multicore 能力预检（证据命令见报告）：OHOS 若禁 fork，mclapply 会报错
    mc_ok <- tryCatch({
        library(parallel)
        x <- mclapply(1:2, function(i) i, mc.cores = 2L)
        all(vapply(x, function(z) !inherits(z, "try-error"), logical(1)))
    }, error = function(e) FALSE)
    if (!isTRUE(mc_ok)) {
        upstream_result <- "SKIPPED"
        upstream_detail <- paste0(
            "OHOS 无 fork/multicore 能力；证据命令: ",
            "Rscript -e 'parallel::mclapply(1:2, function(i) i, mc.cores=2)'")
    } else {
        env <- new.env(parent = globalenv())
        out <- character(0L)
        err <- tryCatch({
            out <- utils::capture.output(source(test_file, local = env))
            NULL
        }, error = function(e) e)
        if (is.null(err)) {
            ok_res <- exists("res", envir = env, inherits = FALSE) &&
                      !is.null(env$res$t)
            if (ok_res) {
                upstream_result <- "PASS"
                upstream_detail <- sprintf(
                    "censboot(parallel='multicore', ncpus=2) 运行成功, 结果是 %d x %d 矩阵",
                    nrow(env$res$t), ncol(env$res$t))
            } else {
                upstream_result <- "FAIL"
                upstream_detail <- "脚本未产生预期 res$t 结果对象"
            }
        } else {
            upstream_result <- "FAIL"
            upstream_detail <- paste0("运行报错: ", conditionMessage(err))
        }
        cat("上游测试标准输出:\n", paste0("  ", out, collapse = "\n"), "\n", sep = "")
    }
}

if (upstream_result == "SKIPPED")
    cat("UPSTREAM_TESTS SKIPPED: ", upstream_detail, "\n", sep = "")
cat(sprintf("UPSTREAM_TESTS_RESULT=%s\n", upstream_result))
cat(sprintf("UPSTREAM_TESTS_DETAIL=%s\n", upstream_detail))

# ==========================================================================
# 步骤 3：50 个 data/*.rda 可 load 校验 + 与 man 数据文档交叉核对
# ==========================================================================
data_dir <- file.path(src_dir, "data")
rda <- sort(list.files(data_dir, pattern = "\\.rda$", full.names = TRUE))
load_ok <- 0L; load_fail <- 0L; load_msgs <- character(0L)
ds_names <- character(0L)
for (f in rda) {
    e <- new.env()
    r <- tryCatch({ load(f, envir = e); NULL }, error = function(er) er)
    nm <- sub("\\.rda$", "", basename(f))
    ds_names <- c(ds_names, nm)
    if (is.null(r) && length(ls(e)) >= 1L) {
        load_ok <- load_ok + 1L
    } else {
        load_fail <- load_fail + 1L
        load_msgs <- c(load_msgs, paste0(nm, ": ",
                      if (is.null(r)) "空对象" else conditionMessage(r)))
    }
}
cat(sprintf("\nDATA_LOAD total=%d loaded=%d failed=%d\n", length(rda), load_ok, load_fail))
if (load_fail > 0L)
    cat(paste0("  载入失败: ", load_msgs, collapse = "\n"), "\n")

# 交叉核对：每个数据集名应在某个 man/*.Rd 的 \alias{} 中出现
man_dir <- file.path(src_dir, "man")
aliases <- character(0L)
for (rd in list.files(man_dir, pattern = "\\.Rd$", full.names = TRUE)) {
    L <- tryCatch(readLines(rd, warn = FALSE), error = function(e) character(0))
    al <- grep("^\\\\alias\\{", L, value = TRUE)
    aliases <- c(aliases, sub("^\\\\alias\\{(.*)\\}\\s*$", "\\1", al))
}
aliases <- unique(aliases)
undocumented <- ds_names[!(ds_names %in% aliases)]
cat(sprintf("DATA_DOC total=%d documented=%d missing=%d\n",
            length(ds_names), length(ds_names) - length(undocumented),
            length(undocumented)))
if (length(undocumented))
    cat("  未在 man 中登记的 alias: ", paste(undocumented, collapse = ", "), "\n", sep = "")

# ==========================================================================
# 汇总退出码：PASS/SKIPPED -> 0；FAIL -> 1
# ==========================================================================
cat("\nUPSTREAM_TESTS SUMMARY:\n")
cat(sprintf("  survival=%s MASS=%s data_loaded=%d/%d data_documented=%d/%d overall=%s\n",
            have_survival, have_mass, load_ok, length(rda),
            length(ds_names) - length(undocumented), length(ds_names), upstream_result))

status <- if (upstream_result == "FAIL" || load_fail > 0L) 1L else 0L
quit(save = "no", status = status)
