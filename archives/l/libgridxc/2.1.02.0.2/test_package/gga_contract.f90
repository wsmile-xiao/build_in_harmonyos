program gga_contract
  use gridXC, only: dp
  use gridXC, only: gridxc_init
  use gridXC, only: gridxc_setXC => gridxc_setXC
  use gridXC, only: ggaxc => gridxc_ggaxc
  implicit none
  real(dp) :: d(1), gd(3,1)
  real(dp) :: epsx, epsc, dexd(1), decd(1), dexdgd(3,1), decdgd(3,1)

  call gridxc_init()
  call gridxc_setXC(1, (/'GGA'/), (/'PBE'/), (/1.0_dp/), (/1.0_dp/))

  d(1) = 0.01_dp
  gd(:,1) = 0.001_dp
  call ggaxc('PBE', 0, 1, d, gd, epsx, epsc, dexd, decd, dexdgd, decdgd)
  if (.not. (epsx < 0.0_dp)) stop 1
  if (.not. (epsc < 0.0_dp)) stop 2
  if (epsx /= epsx) stop 3
  if (epsc /= epsc) stop 4
  if (dexd(1) /= dexd(1)) stop 5
  if (decd(1) /= decd(1)) stop 6

  print *, 'GRIDXC_TEST gga_contract PASS'
end program gga_contract
