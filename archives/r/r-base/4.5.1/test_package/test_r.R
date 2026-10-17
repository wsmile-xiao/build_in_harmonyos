stopifnot(getRversion() == "4.5.1")
stopifnot(identical(2 + 3, 5))
stopifnot(identical(grepl("^Harm.*OS$", "HarmonyOS", perl = TRUE), TRUE))
cp <- crossprod(matrix(c(1, 2, 3, 4), 2, 2))
stopifnot(is.matrix(cp),
          identical(dim(cp), c(2L, 2L)),
          is.null(dimnames(cp)),
          identical(cp, matrix(c(5, 11, 11, 25), 2, 2)),
          identical(drop(cp), cp))
raw <- charToRaw("HarmonyOS R compression")
stopifnot(identical(memDecompress(memCompress(raw, "gzip"), "gzip"), raw))
stopifnot(identical(iconv("HarmonyOS", from = "UTF-8", to = "UTF-8"), "HarmonyOS"))
expected_home <- normalizePath(Sys.getenv("R_HOME"), mustWork = TRUE)
stopifnot(identical(normalizePath(R.home(), mustWork = TRUE), expected_home),
          identical(normalizePath(R.home("share"), mustWork = TRUE), file.path(expected_home, "share")),
          identical(normalizePath(R.home("include"), mustWork = TRUE), file.path(expected_home, "include")),
          identical(normalizePath(R.home("doc"), mustWork = TRUE), file.path(expected_home, "doc")))
https_line <- tryCatch(
    { options(timeout = 20)
      readLines(url("https://cran.r-project.org/"), n = 1L, warn = FALSE) },
    error = function(e) tryCatch(
        { options(timeout = 20)
          readLines(url("https://cran.r-project.org/"), n = 1L, warn = FALSE) },
        error = function(e2) character(0)))
stopifnot(length(https_line) == 1L, nzchar(https_line))
cat("R_BASE_HTTPS=PASS
")
cat("R_BASE_CONSUMER_ASSERTIONS=8/8
")
