#ifndef __OHOS__
#error This is a HarmonyOS-specific native signed-ELF test.
#endif
#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>
#include <mpi.h>
#include <dmumps_c.h>
int main(int argc,char **argv){
    struct utsname u;int rank=0,bad=0,all=0;DMUMPS_STRUC_C id;
    if(MPI_Init(&argc,&argv)!=MPI_SUCCESS)return 1;
    MPI_Comm_rank(MPI_COMM_WORLD,&rank);
    if(uname(&u)!=0 || strcmp(u.sysname,"HarmonyOS") || strcmp(u.machine,"aarch64"))bad=1;
    memset(&id,0,sizeof(id));id.comm_fortran=-987654;id.par=1;id.sym=0;id.job=-1;dmumps_c(&id);
    if(id.infog[0]<0)bad=1;
    id.job=-2;dmumps_c(&id);if(id.infog[0]<0)bad=1;
    MPI_Allreduce(&bad,&all,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if(!all && rank==0){puts("SIGNED_OHOS_ELF_REAL_MPI_MUMPS_PASS");puts("HARMONY_TEST_PASS=1/1");}
    MPI_Finalize();return all?1:0;
}
