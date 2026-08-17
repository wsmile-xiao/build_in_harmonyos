program test_use_mpi
  use mpi
  implicit none
  integer :: ierr, rank, nprocs, value, total, mpi_integer_bytes

  call MPI_Init(ierr)
  if (ierr /= MPI_SUCCESS) error stop 20
  call MPI_Comm_rank(MPI_COMM_WORLD, rank, ierr)
  if (ierr /= MPI_SUCCESS) call MPI_Abort(MPI_COMM_WORLD, 21, ierr)
  call MPI_Comm_size(MPI_COMM_WORLD, nprocs, ierr)
  if (ierr /= MPI_SUCCESS) call MPI_Abort(MPI_COMM_WORLD, 22, ierr)
  if (nprocs /= 2) call MPI_Abort(MPI_COMM_WORLD, 28, ierr)
  call MPI_Type_size(MPI_INTEGER, mpi_integer_bytes, ierr)
  if (ierr /= MPI_SUCCESS) call MPI_Abort(MPI_COMM_WORLD, 23, ierr)
  if (mpi_integer_bytes /= 4 .or. storage_size(rank) / 8 /= 4) then
    call MPI_Abort(MPI_COMM_WORLD, 24, ierr)
  end if

  value = rank + 1
  call MPI_Allreduce(value, total, 1, MPI_INTEGER, MPI_SUM, MPI_COMM_WORLD, ierr)
  if (ierr /= MPI_SUCCESS) call MPI_Abort(MPI_COMM_WORLD, 25, ierr)
  if (total /= nprocs * (nprocs + 1) / 2) then
    call MPI_Abort(MPI_COMM_WORLD, 26, ierr)
  end if
  if (rank == 0) print *, "use mpi i4 ABI: PASS"
  call MPI_Finalize(ierr)
  if (ierr /= MPI_SUCCESS) error stop 27
end program test_use_mpi
