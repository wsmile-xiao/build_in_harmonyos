      program nwchem_mpif4_bridge
      implicit none
      include 'mpif.h'
      integer core_rank,core_size,core_value,core_sum,expected_sum
      integer*4 stupid_world,stupid_sum,stupid_integer
      integer*4 stupid_rank,stupid_size,stupid_count,stupid_ierr
      integer*4 mpi_value,mpi_total_i4,abort_code

      stupid_ierr = -1
      call MPI_Init(stupid_ierr)
      if (stupid_ierr.ne.MPI_SUCCESS) stop 91
      stupid_world = MPI_COMM_WORLD
      stupid_sum = MPI_SUM
      stupid_integer = MPI_INTEGER
      stupid_count = 1
      call MPI_Comm_rank(stupid_world,stupid_rank,stupid_ierr)
      if (stupid_ierr.ne.MPI_SUCCESS) then
         abort_code = 92
         call MPI_Abort(stupid_world,abort_code,stupid_ierr)
         stop 92
      endif
      call MPI_Comm_size(stupid_world,stupid_size,stupid_ierr)
      if (stupid_ierr.ne.MPI_SUCCESS) then
         abort_code = 93
         call MPI_Abort(stupid_world,abort_code,stupid_ierr)
         stop 93
      endif

      core_rank = stupid_rank
      core_size = stupid_size
      core_value = core_rank + 1
      mpi_value = int(core_value,kind=4)
      mpi_total_i4 = -2147483647
      call MPI_Allreduce(mpi_value,mpi_total_i4,stupid_count,
     >                   stupid_integer,stupid_sum,stupid_world,
     >                   stupid_ierr)
      if (stupid_ierr.ne.MPI_SUCCESS) then
         abort_code = 94
         call MPI_Abort(stupid_world,abort_code,stupid_ierr)
         stop 94
      endif
      core_sum = mpi_total_i4
      expected_sum = core_size*(core_size+1)/2

      if ((bit_size(core_value).ne.64).or.
     >    (bit_size(stupid_count).ne.32).or.
     >    (core_size.ne.2).or.(core_sum.ne.expected_sum)) then
         abort_code = 91
         call MPI_Abort(stupid_world,abort_code,stupid_ierr)
         stop 95
      endif
      call MPI_Finalize(stupid_ierr)
      if (stupid_ierr.ne.MPI_SUCCESS) stop 96
      if (stupid_rank.eq.0) then
         write(*,'(A)') 'NWChem USE_MPIF4 i8/i4 bridge: PASS'
      endif
      end
