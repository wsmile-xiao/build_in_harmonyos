program test_mixed
  use, intrinsic :: iso_c_binding, only : c_int
  implicit none
  include 'mpif.h'

  interface
    function c_mpi_probe(comm_f, fortran_rank, fortran_size) &
        bind(C, name="c_mpi_probe") result(status)
      import :: c_int
      integer(c_int), value :: comm_f, fortran_rank, fortran_size
      integer(c_int) :: status
    end function c_mpi_probe
  end interface

  integer :: ierr, rank, nprocs
  integer(c_int) :: status

  call MPI_Init(ierr)
  if (ierr /= MPI_SUCCESS) error stop 40
  call MPI_Comm_rank(MPI_COMM_WORLD, rank, ierr)
  if (ierr /= MPI_SUCCESS) call MPI_Abort(MPI_COMM_WORLD, 41, ierr)
  call MPI_Comm_size(MPI_COMM_WORLD, nprocs, ierr)
  if (ierr /= MPI_SUCCESS) call MPI_Abort(MPI_COMM_WORLD, 42, ierr)
  if (nprocs /= 2) call MPI_Abort(MPI_COMM_WORLD, 45, ierr)

  status = c_mpi_probe(int(MPI_COMM_WORLD, c_int), &
                       int(rank, c_int), int(nprocs, c_int))
  if (status /= 0_c_int) call MPI_Abort(MPI_COMM_WORLD, 43, ierr)
  if (rank == 0) print *, "mixed C/Fortran MPI_Fint i4 ABI: PASS"

  call MPI_Finalize(ierr)
  if (ierr /= MPI_SUCCESS) error stop 44
end program test_mixed
