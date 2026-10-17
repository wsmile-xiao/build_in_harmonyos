program test_libxc_fortran_kxc
  use, intrinsic :: iso_c_binding
  use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
  use xc_f03_lib_m
  implicit none

  type(xc_f03_func_t) :: func
  type(xc_f03_func_info_t) :: info
  integer(c_int) :: flags, major, minor, micro
  real(c_double), parameter :: tolerance = 1.0e-11_c_double
  real(c_double) :: rho(2), zk(2), vrho(2), v2rho2(2), v3rho3(2)
  real(c_double) :: expected_zk(2), expected_vrho(2)
  real(c_double) :: expected_v2rho2(2), expected_v3rho3(2), cx

  call xc_f03_version(major, minor, micro)
  if (major /= 7_c_int .or. minor /= 1_c_int .or. micro /= 2_c_int) then
    error stop 10
  end if

  call xc_f03_func_init(func, 1_c_int, XC_UNPOLARIZED)
  info = xc_f03_func_get_info(func)
  flags = xc_f03_func_info_get_flags(info)
  if (iand(flags, XC_FLAGS_HAVE_KXC) == 0_c_int) then
    call xc_f03_func_end(func)
    error stop 11
  end if
  if (iand(flags, XC_FLAGS_HAVE_LXC) /= 0_c_int) then
    call xc_f03_func_end(func)
    error stop 14
  end if

  rho = [0.25_c_double, 0.5_c_double]
  call xc_f03_lda_exc_vxc_fxc_kxc(func, 2_c_size_t, rho, zk, vrho, v2rho2, v3rho3)
  if (.not. all(ieee_is_finite(zk)) .or. .not. all(ieee_is_finite(vrho)) .or. &
      .not. all(ieee_is_finite(v2rho2)) .or. .not. all(ieee_is_finite(v3rho3))) then
    call xc_f03_func_end(func)
    error stop 12
  end if

  cx = 0.75_c_double * (3.0_c_double / acos(-1.0_c_double))**(1.0_c_double / 3.0_c_double)
  expected_zk = -cx * rho**(1.0_c_double / 3.0_c_double)
  expected_vrho = -(4.0_c_double / 3.0_c_double) * cx * rho**(1.0_c_double / 3.0_c_double)
  expected_v2rho2 = -(4.0_c_double / 9.0_c_double) * cx * rho**(-2.0_c_double / 3.0_c_double)
  expected_v3rho3 = (8.0_c_double / 27.0_c_double) * cx * rho**(-5.0_c_double / 3.0_c_double)
  if (maxval(abs(zk - expected_zk) / max(1.0_c_double, abs(expected_zk))) > tolerance .or. &
      maxval(abs(vrho - expected_vrho) / max(1.0_c_double, abs(expected_vrho))) > tolerance .or. &
      maxval(abs(v2rho2 - expected_v2rho2) / max(1.0_c_double, abs(expected_v2rho2))) > tolerance .or. &
      maxval(abs(v3rho3 - expected_v3rho3) / max(1.0_c_double, abs(expected_v3rho3))) > tolerance) then
    call xc_f03_func_end(func)
    error stop 13
  end if

  call xc_f03_func_end(func)
  write(*, '(A)') 'Libxc 7.1.2 Fortran KXC consumer: PASS'
end program test_libxc_fortran_kxc
