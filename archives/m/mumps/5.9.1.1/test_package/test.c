#include <math.h>
#include <stdio.h>
#include <string.h>
#include <mpi.h>
#include <dmumps_c.h>

int main(int argc,char **argv) {
    int rank=0,fail=0,all=0;
    MUMPS_INT rows[2]={1,2},cols[2]={1,2};
    double matrix[2]={2.0,3.0},rhs[2]={2.0,6.0};
    DMUMPS_STRUC_C id;
    if(MPI_Init(&argc,&argv)!=MPI_SUCCESS)return 1;
    MPI_Comm_rank(MPI_COMM_WORLD,&rank);
    memset(&id,0,sizeof(id));id.comm_fortran=-987654;id.par=1;id.sym=0;id.job=-1;
    dmumps_c(&id);
    if(id.infog[0]<0 || sizeof(MUMPS_INT)!=4)fail=1;
    id.icntl[0]=-1;id.icntl[1]=-1;id.icntl[2]=-1;id.icntl[3]=0;
    if(rank==0){id.n=2;id.nnz=2;id.irn=rows;id.jcn=cols;id.a=matrix;id.rhs=rhs;}
    id.job=1;dmumps_c(&id);if(id.infog[0]<0)fail=1;
    MPI_Allreduce(&fail,&all,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if(!all && rank==0)puts("CONSUMER_CASE_PASS=real_mpi_analysis");
    id.job=2;dmumps_c(&id);if(id.infog[0]<0)fail=1;
    MPI_Allreduce(&fail,&all,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if(!all && rank==0)puts("CONSUMER_CASE_PASS=parallel_factorization");
    id.job=3;dmumps_c(&id);
    if(id.infog[0]<0 || (rank==0 && (fabs(rhs[0]-1)>1e-12 || fabs(rhs[1]-2)>1e-12)))fail=1;
    MPI_Allreduce(&fail,&all,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if(!all && rank==0)puts("CONSUMER_CASE_PASS=numerical_solve");
    if(rank==0){rhs[0]=4.0;rhs[1]=9.0;}
    id.job=3;dmumps_c(&id);
    if(id.infog[0]<0 || (rank==0 && (fabs(rhs[0]-2)>1e-12 || fabs(rhs[1]-3)>1e-12)))fail=1;
    MPI_Allreduce(&fail,&all,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if(!all && rank==0)puts("CONSUMER_CASE_PASS=reuse_factorization");
    id.job=-2;dmumps_c(&id);if(id.infog[0]<0)fail=1;
    MPI_Allreduce(&fail,&all,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if(!all && rank==0)puts("CONSUMER_TEST_PASS=4/4");
    MPI_Finalize();return all?1:0;
}
