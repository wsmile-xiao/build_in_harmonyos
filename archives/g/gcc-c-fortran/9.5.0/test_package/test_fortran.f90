program test_fortran_ohos
  ! Real Fortran program exercising floating-point arithmetic, arrays,
  ! intrinsics and formatted I/O.  Used to validate the packaged gfortran
  ! toolchain: source must compile, link and execute on HarmonyOS AArch64.
  implicit none
  integer, parameter :: dp = kind(1.0d0)
  real(dp) :: a(4), b(4), c(4)
  real(dp) :: dot, scale
  integer :: i, n
  integer :: unit, ios
  character(len=64) :: line

  ! Array construction and element-wise arithmetic
  do i = 1, 4
     a(i) = real(i, dp)
  end do
  b = 2.0_dp * a
  c = a + b
  if (any(abs(c - 3.0_dp * a) > 1.0e-12_dp)) then
     error stop "array arithmetic failed"
  end if

  ! Intrinsic reduction (dot_product, sum)
  dot = dot_product(a, b)
  if (abs(dot - 60.0_dp) > 1.0e-9_dp) then
     error stop "dot_product failed"
  end if
  if (abs(sum(a) - 10.0_dp) > 1.0e-12_dp) then
     error stop "sum failed"
  end if

  ! Scalar floating-point operations (pow, transcendental functions)
  scale = 2.0_dp ** 10.0_dp
  if (abs(scale - 1024.0_dp) > 1.0e-9_dp) then
     error stop "power failed"
  end if
  if (abs(cos(0.0_dp) - 1.0_dp) > 1.0e-12_dp) then
     error stop "cos failed"
  end if

  ! Formatted I/O through the libgfortran runtime
  open(newunit=unit, status='scratch', action='readwrite', iostat=ios)
  if (ios /= 0) then
     error stop "open failed"
  end if
  write(unit, '(a,i0,a)') 'gfortran9-ohos-ok value=', nint(dot), ''
  rewind(unit)
  read(unit, '(a)', iostat=ios) line
  close(unit)
  if (ios /= 0 .or. index(line, 'gfortran9-ohos-ok') == 0) then
     error stop "formatted I/O failed"
  end if

  write(*, '(a)') trim(line)
  write(*, '(a)') 'gfortran test PASSED'
end program test_fortran_ohos