# base R 最小 testthat 替代（P2 修复：expect_equal 用绝对容差语义）
context <- function(...) invisible(NULL)
.env <- new.env(parent = emptyenv())
.env$pass <- 0L
.env$fail <- 0L
.env$failures <- character(0)
test_that <- function(desc, code) {
  err <- tryCatch({ force(code); NULL }, error = function(e) e)
  if (is.null(err)) { .env$pass <- .env$pass + 1L; cat("PASS:", desc, "\n") }
  else {
    .env$fail <- .env$fail + 1L
    msg <- conditionMessage(err)
    .env$failures <- c(.env$failures, paste0(desc, ": ", msg))
    cat("FAIL:", desc, "->", msg, "\n")
  }
}
expect_true <- function(x) if (!isTRUE(x)) stop("expect_true failed")
expect_equal <- function(object, expected, tolerance = NULL, ..., tol = NULL) {
  if (is.null(tolerance) && !is.null(tol)) tolerance <- tol
  if (is.null(tolerance)) tolerance <- 1.5e-8
  # P2 修复：上游 tol= 参数本意为绝对容差；改用 |object - expected| <= tolerance
  #（避免 all.equal 相对容差把 ULP 级浮点差异放大为断言失败）
  if (is.numeric(object) && is.numeric(expected)) {
    if (length(object) != length(expected))
      stop("expect_equal failed: length mismatch (", length(object), " vs ", length(expected), ")")
    if (any(abs(object - expected) > tolerance))
      stop("expect_equal failed: got ", paste(head(object,3), collapse=","),
           " expected ", paste(head(expected,3), collapse=","),
           " tolerance=", tolerance)
  } else if (!isTRUE(all.equal(object, expected, tolerance = tolerance, check.attributes = FALSE))) {
    stop("expect_equal failed: got ", paste(head(object,3), collapse=","),
         " expected ", paste(head(expected,3), collapse=","))
  }
}
expect_error <- function(expr, regexp = NULL, ...) {
  err <- tryCatch({ force(expr); NULL }, error = function(e) e)
  if (is.null(err)) stop("expected error but none thrown")
  if (!is.null(regexp) && !grepl(regexp, conditionMessage(err), perl=TRUE)) stop("error msg mismatch")
}
expect_warning <- function(expr, regexp = NULL, ...) {
  ws <- character(0)
  withCallingHandlers(force(expr), warning = function(w) { ws <<- c(ws, conditionMessage(w)); invokeRestart("muffleWarning") })
  if (length(ws) == 0) stop("expected warning but none")
  if (!is.null(regexp) && !any(grepl(regexp, ws, perl=TRUE))) stop("warning msg mismatch")
}
expect_no_error <- function(expr, ...) {
  err <- tryCatch({ force(expr); NULL }, error = function(e) e)
  if (!is.null(err)) stop("unexpected error: ", conditionMessage(err))
}
test_check <- function(pkg) invisible(NULL)
