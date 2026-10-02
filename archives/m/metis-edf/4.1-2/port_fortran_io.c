/*
 * Portable C port of the three small Fortran I/O helpers used by onmetis in
 * metis-edf-4.1 (Code_Aster):
 *
 *   Programs/lect00.f  -> lect00_()
 *   Programs/lect11.f  -> lect11_()
 *   Programs/ecri11.f  -> ecri11_()
 *
 * The upstream build needs a Fortran compiler (gfortran) for these three
 * routines only; the rest of metis-edf is plain C.  This file reproduces their
 * fixed-format (FILE='fort.81' / UNIT=85) behaviour using ISO C so the whole
 * package builds with the OHOS clang toolchain.  The original .f sources stay
 * in the tree untouched for reference.
 */
#include <stdio.h>
#include <stdlib.h>

#include <metis.h> /* idxtype */

static FILE *open_fort81(void)
{
    FILE *fp = fopen("fort.81", "r");
    if (fp == NULL) {
        printf("Failed to open file fort.81\n");
        exit(4);
    }
    return fp;
}

/*
 * lect00.f:
 *   rewind 81 ; read(81,1001) n,ll          ! FORMAT(8I10)
 */
void lect00_(long *n, long *ll)
{
    FILE *fp = open_fort81();
    if (fscanf(fp, "%ld %ld", n, ll) != 2) {
        printf("lect00: malformed fort.81 header\n");
        fclose(fp);
        exit(4);
    }
    fclose(fp);
}

/*
 * lect11.f:
 *   rewind 81
 *   read(81,1001) n,ll,niv,ifm              ! FORMAT(8I10)
 *   read(81,1001) (xadj(i),i=1,n+1)
 *   do j=1,n ; read(81,1000) (adjncy(i),i=xadj(j),xadj(j+1)-1) ; enddo
 *   do i=1,n+1 ; xadj(i)=xadj(i)-1 ; enddo
 *   do i=1,long ; adjncy(i)=adjncy(i)-1 ; enddo
 *
 * The leading "ll" of the file is read into a *local* (as in the Fortran
 * routine); the dummy argument "long_" keeps the caller's value
 * (= 2*nedges in io_aster.c) and that value drives the adjncy renumbering.
 */
void lect11_(long *n, long *long_, long *xadj, long *adjncy, long *niv, long *ifm)
{
    FILE *fp = open_fort81();
    long nf, llf, nivf, ifmf, i, j, deb, fin;

    if (fscanf(fp, "%ld %ld %ld %ld", &nf, &llf, &nivf, &ifmf) != 4) {
        printf("lect11: malformed fort.81 header\n");
        fclose(fp);
        exit(4);
    }
    *n = nf;
    *niv = nivf;
    *ifm = ifmf;

    for (i = 0; i < *n + 1; i++) {
        if (fscanf(fp, "%ld", &xadj[i]) != 1) {
            printf("lect11: short xadj\n");
            fclose(fp);
            exit(4);
        }
    }
    if (*niv >= 1)
        printf("Metis nombres de noeuds, d'aretes   %ld %ld\n", *n, llf);

    for (j = 1; j <= *n; j++) {
        deb = xadj[j - 1];
        fin = xadj[j] - 1;
        for (i = deb; i <= fin; i++) {
            if (fscanf(fp, "%ld", &adjncy[i - 1]) != 1) {
                printf("lect11: short adjncy\n");
                fclose(fp);
                exit(4);
            }
        }
    }
    if (*niv >= 1)
        printf("Metis Tableau Xadj lu  \n");

    for (i = 0; i < *n + 1; i++)
        xadj[i] -= 1;
    for (i = 0; i < *long_; i++)
        adjncy[i] -= 1;

    fclose(fp);
}

static void write_i10(FILE *fp, const long *v, long count, int per_line)
{
    long i;
    for (i = 0; i < count; i++) {
        fprintf(fp, "%10ld", v[i]);
        if ((i % per_line) == per_line - 1 || i == count - 1)
            fputc('\n', fp);
    }
}

/* Fortran E20.6 field: d.ddddddE+/-ee, right justified into 20 columns. */
static void write_e20_6(FILE *fp, double value)
{
    char field[32];
    double a;
    int neg, exp;
    long mant;

    neg = (value < 0.0);
    a = neg ? -value : value;
    exp = 0;
    if (a != 0.0) {
        while (a >= 1.0) { a /= 10.0; exp++; }
        while (a < 0.1)  { a *= 10.0; exp--; }
    }
    mant = (long)(a * 1000000.0 + 0.5);
    if (mant >= 1000000L) { mant /= 10L; exp++; }
    snprintf(field, sizeof(field), "%s0.%06ldE%+03d",
             neg ? "-" : "", mant, exp);
    fprintf(fp, "%20s", field);
}

/*
 * ecri11.f:
 *   open(FILE='fort.85',UNIT=85,FORM='FORMATTED') ; rewind 85
 *   print *,' METIS_ecri11 ', nbsn,opc,maxlnz,lgind
 *   write(85,1001) nbsn,opc,maxlnz,lgind    ! FORMAT(I10,E20.6,2I10)
 *   write(85,1000) (invp(i+1),i=1,n)        ! FORMAT(8I10)
 *   write(85,1000) (perm(i+1),i=1,n)
 *   write(85,1000) (supnd(i+1),i=1,nbsn+1)
 *   write(85,1000) (parent(i+1),i=1,nbsn)
 *
 * The pointers arrive already shifted by "-1" in smbfactor.c so that the
 * Fortran-style 1-based index maps to p[i].
 */
void ecri11_(long *invp, long *perm, long *supnd, long *parent,
             long *n, long *nbsn, double *opc, long *maxlnz, long *lgind)
{
    FILE *fp = fopen("fort.85", "w");
    if (fp == NULL) {
        printf("Failed to open file fort.85\n");
        exit(4);
    }

    printf(" METIS_ecri11  %ld %g %ld %ld\n", *nbsn, *opc, *maxlnz, *lgind);

    fprintf(fp, "%10ld", *nbsn);
    write_e20_6(fp, *opc);
    fprintf(fp, "%10ld%10ld\n", *maxlnz, *lgind);

    write_i10(fp, invp + 1, *n, 8);
    write_i10(fp, perm + 1, *n, 8);
    write_i10(fp, supnd + 1, *nbsn + 1, 8);
    write_i10(fp, parent + 1, *nbsn, 8);

    fclose(fp);
}
