# acepack test_package 验证脚本（OHOS aarch64）
# 真实调用 ace()/avas() 核心 API，禁止空壳（R34）
suppressPackageStartupMessages(library(acepack))

cat("ACEPACK_VERSION:", as.character(packageVersion("acepack")), "\n")

# 构造回归数据
set.seed(2026)
n <- 200
x1 <- runif(n)
x2 <- runif(n)
y <- sin(2 * pi * x1) + 0.5 * x2 + rnorm(n, sd = 0.1)
dat <- data.frame(x1 = x1, x2 = x2, y = y)

# ace(): 交替条件期望（核心 API）；tx 为 n x p 矩阵（上游 ace.R: tx <- x）
fit <- ace(dat[, c("x1", "x2")], dat$y)
stopifnot(is.list(fit))
stopifnot(!is.null(fit$tx), !is.null(fit$ty))
stopifnot(is.matrix(fit$tx), nrow(fit$tx) == n)
stopifnot(length(fit$ty) == n)
cat("ACEPACK_ACE_OK\n")

# avas(): 方差稳定化变换（核心 API）；tx 为 n x p 矩阵（上游 avas.R: tx <- x）
fit2 <- avas(dat[, c("x1", "x2")], dat$y)
stopifnot(is.list(fit2))
stopifnot(!is.null(fit2$tx), !is.null(fit2$ty))
stopifnot(is.matrix(fit2$tx), nrow(fit2$tx) == n)
stopifnot(length(fit2$ty) == n)
cat("ACEPACK_AVAS_OK\n")

cat("ACEPACK_TEST_ALL_OK\n")
