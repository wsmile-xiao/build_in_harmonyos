      program test_mpifh
      include 'mpif.h'
      integer ierr, rank, nprocs, value, total, mpi_integer_bytes

      call MPI_INIT(ierr)
      if (ierr .ne. MPI_SUCCESS) stop 10
      call MPI_COMM_RANK(MPI_COMM_WORLD, rank, ierr)
      if (ierr .ne. MPI_SUCCESS) call MPI_ABORT(MPI_COMM_WORLD, 11,
     &                                         ierr)
      call MPI_COMM_SIZE(MPI_COMM_WORLD, nprocs, ierr)
      if (ierr .ne. MPI_SUCCESS) call MPI_ABORT(MPI_COMM_WORLD, 12,
     &                                         ierr)
      if (nprocs .ne. 2) call MPI_ABORT(MPI_COMM_WORLD, 19, ierr)
      call MPI_TYPE_SIZE(MPI_INTEGER, mpi_integer_bytes, ierr)
      if (ierr .ne. MPI_SUCCESS) call MPI_ABORT(MPI_COMM_WORLD, 13,
     &                                         ierr)
      if (mpi_integer_bytes .ne. 4) call MPI_ABORT(MPI_COMM_WORLD, 14,
     &                                             ierr)
      if (bit_size(rank) / 8 .ne. 4) call MPI_ABORT(MPI_COMM_WORLD,
     &                                              15, ierr)

      value = rank + 1
      call MPI_ALLREDUCE(value, total, 1, MPI_INTEGER, MPI_SUM,
     &                   MPI_COMM_WORLD, ierr)
      if (ierr .ne. MPI_SUCCESS) call MPI_ABORT(MPI_COMM_WORLD, 16,
     &                                         ierr)
      if (total .ne. nprocs * (nprocs + 1) / 2) then
         call MPI_ABORT(MPI_COMM_WORLD, 17, ierr)
      endif
      if (rank .eq. 0) print *, 'mpif.h i4 ABI: PASS'
      call MPI_FINALIZE(ierr)
      if (ierr .ne. MPI_SUCCESS) stop 18
      end
