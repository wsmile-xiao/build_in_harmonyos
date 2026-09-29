program lda_contract
  use gridXC, only: dp
  use gridXC, only: gridxc_init
  use gridXC, only: gridxc_setXC => gridxc_setXC
  use gridXC, only: gridxc_getXC => gridxc_getXC
  use gridXC, only: ldaxc => gridxc_ldaxc
  implicit none
  integer :: n
  character(len=50) :: func(1), auth(1)
  real(dp) :: wx(1), wc(1)
  real(dp) :: d(1), epsx, epsc, vx(1), vc(1)
  real(dp) :: dvxdn(1,1), dvcdn(1,1)

  call gridxc_init()
  call gridxc_setXC(1, (/'LDA'/), (/'PZ '/), (/1.0_dp/), (/1.0_dp/))
  call gridxc_getXC(n, func, auth, wx, wc)
  if (n /= 1) stop 1
  if (trim(func(1)) /= 'LDA') stop 2
  if (trim(auth(1)) /= 'PZ') stop 3

  d(1) = 0.01_dp
  call ldaxc('PZ', 0, 1, d, epsx, epsc, vx, vc, dvxdn, dvcdn)
  if (.not. (epsx < 0.0_dp)) stop 4
  if (.not. (epsc < 0.0_dp)) stop 5
  if (.not. (vx(1) < 0.0_dp)) stop 6
  if (.not. (vc(1) < 0.0_dp)) stop 7
  if (epsx /= epsx) stop 8
  if (epsc /= epsc) stop 9

  print *, 'GRIDXC_TEST lda_contract PASS'
end program lda_contract
