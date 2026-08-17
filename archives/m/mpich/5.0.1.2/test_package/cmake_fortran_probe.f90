subroutine cmake_fortran_probe(comm_f, status) bind(C, name="cmake_fortran_probe")
  use, intrinsic :: iso_c_binding, only : c_int32_t
  implicit none
  include 'mpif.h'

  integer(c_int32_t), value :: comm_f
  integer(c_int32_t), intent(out) :: status
  integer :: rank, nprocs, ierr, value, total

  status = 121_c_int32_t
  call MPI_Comm_rank(comm_f, rank, ierr)
  if (ierr /= MPI_SUCCESS) return
  status = 122_c_int32_t
  call MPI_Comm_size(comm_f, nprocs, ierr)
  if (ierr /= MPI_SUCCESS .or. nprocs /= 2) return
  status = 123_c_int32_t
  value = rank + 1
  call MPI_Allreduce(value, total, 1, MPI_INTEGER, MPI_SUM, comm_f, ierr)
  if (ierr /= MPI_SUCCESS .or. total /= 3) return
  status = 0_c_int32_t
end subroutine cmake_fortran_probe
