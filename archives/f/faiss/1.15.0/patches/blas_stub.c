/*
 * Minimal BLAS/LAPACK stub for FAISS on HarmonyOS.
 * BLAS: sgemm_, dgemm_, sgemv_ (functional implementations)
 * LAPACK: sgeqrf_, sorgqr_, sgetrf_, sgetri_, sgesvd_, sgelsd_,
 *         dgetrf_, dgetri_, dgesvd_ (stubs that set info=-1 = not implemented)
 */
#include <string.h>
#include <stddef.h>

/* ===== BLAS (functional) ===== */

void sgemm_(const char *transa, const char *transb,
            const int *pm, const int *pn, const int *pk,
            const float *alpha, const float *A, const int *lda,
            const float *B, const int *ldb,
            const float *beta, float *C, const int *ldc)
{
    int m = *pm, n = *pn, k = *pk;
    int na = (*transa == 'N' || *transa == 'n');
    int nb = (*transb == 'N' || *transb == 'n');
    float a = *alpha, b = *beta;

    if (b == 0.0f) {
        for (int j = 0; j < n; j++)
            memset(&C[j * (*ldc)], 0, m * sizeof(float));
    } else {
        for (int j = 0; j < n; j++)
            for (int i = 0; i < m; i++)
                C[j * (*ldc) + i] *= b;
    }

    for (int j = 0; j < n; j++) {
        for (int i = 0; i < m; i++) {
            float sum = 0.0f;
            if (na && nb) {
                for (int l = 0; l < k; l++)
                    sum += A[l * (*lda) + i] * B[j * (*ldb) + l];
            } else if (na) {
                for (int l = 0; l < k; l++)
                    sum += A[l * (*lda) + i] * B[l * (*ldb) + j];
            } else if (nb) {
                for (int l = 0; l < k; l++)
                    sum += A[i * (*lda) + l] * B[j * (*ldb) + l];
            } else {
                for (int l = 0; l < k; l++)
                    sum += A[i * (*lda) + l] * B[l * (*ldb) + j];
            }
            C[j * (*ldc) + i] += a * sum;
        }
    }
}

void dgemm_(const char *transa, const char *transb,
            const int *pm, const int *pn, const int *pk,
            const double *alpha, const double *A, const int *lda,
            const double *B, const int *ldb,
            const double *beta, double *C, const int *ldc)
{
    int m = *pm, n = *pn, k = *pk;
    int na = (*transa == 'N' || *transa == 'n');
    int nb = (*transb == 'N' || *transb == 'n');
    double a = *alpha, b = *beta;

    if (b == 0.0) {
        for (int j = 0; j < n; j++)
            memset(&C[j * (*ldc)], 0, m * sizeof(double));
    } else {
        for (int j = 0; j < n; j++)
            for (int i = 0; i < m; i++)
                C[j * (*ldc) + i] *= b;
    }

    for (int j = 0; j < n; j++) {
        for (int i = 0; i < m; i++) {
            double sum = 0.0;
            if (na && nb) {
                for (int l = 0; l < k; l++)
                    sum += A[l * (*lda) + i] * B[j * (*ldb) + l];
            } else if (na) {
                for (int l = 0; l < k; l++)
                    sum += A[l * (*lda) + i] * B[l * (*ldb) + j];
            } else if (nb) {
                for (int l = 0; l < k; l++)
                    sum += A[i * (*lda) + l] * B[j * (*ldb) + l];
            } else {
                for (int l = 0; l < k; l++)
                    sum += A[i * (*lda) + l] * B[l * (*ldb) + j];
            }
            C[j * (*ldc) + i] += a * sum;
        }
    }
}

void sgemv_(const char *trans, const int *pm, const int *pn,
            const float *alpha, const float *A, const int *lda,
            const float *x, const int *incx,
            const float *beta, float *y, const int *incy)
{
    int m = *pm, n = *pn;
    int nt = (*trans == 'N' || *trans == 'n');
    float a = *alpha, b = *beta;
    int len_y = nt ? m : n;

    if (b == 0.0f) {
        for (int i = 0; i < len_y; i++)
            y[i * (*incy)] = 0.0f;
    } else {
        for (int i = 0; i < len_y; i++)
            y[i * (*incy)] *= b;
    }

    if (nt) {
        for (int j = 0; j < n; j++) {
            float xj = x[j * (*incx)];
            for (int i = 0; i < m; i++)
                y[i * (*incy)] += a * A[j * (*lda) + i] * xj;
        }
    } else {
        for (int j = 0; j < n; j++) {
            float sum = 0.0f;
            for (int i = 0; i < m; i++)
                sum += A[j * (*lda) + i] * x[i * (*incx)];
            y[j * (*incy)] += a * sum;
        }
    }
}

/* ===== LAPACK stubs (no-op, set info=-1 to signal not implemented) ===== */
/* These are used by FAISS matrix_qr/matrix_inverse which are not
   called in the IndexFlat test path. They exist for link resolution.
   info=-1 signals "argument error / not available" per LAPACK convention. */

void sgeqrf_(const int *m, const int *n, float *a, const int *lda,
             float *tau, float *work, const int *lwork, int *info)
{
    *info = -1;
}

void sorgqr_(const int *m, const int *n, const int *k, float *a,
             const int *lda, const float *tau, float *work,
             const int *lwork, int *info)
{
    *info = -1;
}

void sgetrf_(const int *m, const int *n, float *a, const int *lda,
             int *ipiv, int *info)
{
    *info = -1;
}

void sgetri_(const int *n, float *a, const int *lda, const int *ipiv,
             float *work, const int *lwork, int *info)
{
    *info = -1;
}

void dgetrf_(const int *m, const int *n, double *a, const int *lda,
             int *ipiv, int *info)
{
    *info = -1;
}

void dgetri_(const int *n, double *a, const int *lda, const int *ipiv,
             double *work, const int *lwork, int *info)
{
    *info = -1;
}

void sgesvd_(const char *jobu, const char *jobvt, const int *m, const int *n,
             float *a, const int *lda, float *s, float *u, const int *ldu,
             float *vt, const int *ldvt, float *work, const int *lwork,
             int *info)
{
    *info = -1;
}

void dgesvd_(const char *jobu, const char *jobvt, const int *m, const int *n,
             double *a, const int *lda, double *s, double *u, const int *ldu,
             double *vt, const int *ldvt, double *work, const int *lwork,
             int *info)
{
    *info = -1;
}

void sgelsd_(const int *m, const int *n, const int *nrhs, float *a,
             const int *lda, float *b, const int *ldb, float *s,
             const float *rcond, int *rank, float *work, const int *lwork,
             int *iwork, int *info)
{
    *info = -1;
}
