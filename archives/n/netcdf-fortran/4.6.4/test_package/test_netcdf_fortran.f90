! test_netcdf_fortran.f90 — netcdf-fortran 消费者实测（Conan test_package）
!
! 真实使用 Fortran 2003 API（use netcdf）跑完整数据链路：
!   建 netCDF-4 文件 → 定义维度/变量 → 写属性 → 开启 HDF5 deflate → 写数据
!   → 关闭 → 只读重开 → 逐项回读校验（格式/变量元数据/维度长度/属性/数据）
! 任一断言失败即以非零码退出，保证 conan create 的 test_package 阶段真实失败。
program test_netcdf_fortran
  use netcdf
  implicit none

  integer, parameter :: NX = 4, NY = 3
  character(len=*), parameter :: FILE_NAME = "test_netcdf_fortran.nc"
  character(len=*), parameter :: VAR_NAME = "temp"
  character(len=*), parameter :: UNITS = "degC"

  integer :: ncid, dimids(2), varid, checks, failures
  integer :: fmt, ndims, nvars, natts, unlimdim, ndimsv, nattsv, dimlen, xtype
  real(8) :: written(NX, NY), readback(NX, NY)
  character(len=NF90_MAX_NAME) :: vname, dname, units_out
  character(len=80) :: libvers
  integer :: i, j

  checks = 0
  failures = 0

  ! ① Fortran 层 nf_inq_libvers 转发 netcdf-c 的版本串（源码事实），
  !    借此确认本库确实链在预期的 netcdf-c 4.9.3 上。
  libvers = nf90_inq_libvers()
  call check(index(trim(libvers), "4.9.3") == 1, &
             "nf90_inq_libvers() 转发 netcdf-c 版本: " // trim(libvers))

  ! ② 建 netCDF-4 文件
  call check(nf90_create(FILE_NAME, ior(NF90_NETCDF4, NF90_CLOBBER), ncid) == NF90_NOERR, &
             "nf90_create(NF90_NETCDF4)")
  call check(nf90_def_dim(ncid, "x", NX, dimids(1)) == NF90_NOERR, "nf90_def_dim x")
  call check(nf90_def_dim(ncid, "y", NY, dimids(2)) == NF90_NOERR, "nf90_def_dim y")
  call check(nf90_def_var(ncid, VAR_NAME, NF90_DOUBLE, dimids, varid) == NF90_NOERR, &
             "nf90_def_var NF90_DOUBLE")
  call check(nf90_put_att(ncid, varid, "units", UNITS) == NF90_NOERR, "nf90_put_att units")
  call check(nf90_def_var_deflate(ncid, varid, 0, 1, 1) == NF90_NOERR, &
             "nf90_def_var_deflate（HDF5 压缩链路）")
  call check(nf90_enddef(ncid) == NF90_NOERR, "nf90_enddef")

  do j = 1, NY
    do i = 1, NX
      written(i, j) = dble(i) * 100.0d0 + dble(j)
    end do
  end do
  call check(nf90_put_var(ncid, varid, written) == NF90_NOERR, "nf90_put_var")
  call check(nf90_close(ncid) == NF90_NOERR, "nf90_close")

  ! ③ 只读重开并逐项校验
  call check(nf90_open(FILE_NAME, NF90_NOWRITE, ncid) == NF90_NOERR, "nf90_open")
  call check(nf90_inquire(ncid, nDimensions=ndims, nVariables=nvars, nAttributes=natts, &
                          unlimitedDimId=unlimdim, formatNum=fmt) == NF90_NOERR, &
             "nf90_inquire")
  call check(fmt == NF90_FORMAT_NETCDF4, "文件格式为 NF90_FORMAT_NETCDF4")
  call check(ndims == 2 .and. nvars == 1, "维度数=2 变量数=1")

  call check(nf90_inq_varid(ncid, VAR_NAME, varid) == NF90_NOERR, "nf90_inq_varid")
  call check(nf90_inquire_variable(ncid, varid, name=vname, xtype=xtype, ndims=ndimsv, &
                                   dimids=dimids, nAtts=nattsv) == NF90_NOERR, &
             "nf90_inquire_variable")
  call check(trim(vname) == VAR_NAME, "变量名一致")
  call check(xtype == NF90_DOUBLE, "变量类型为 NF90_DOUBLE")
  call check(ndimsv == 2, "变量维度数=2")
  call check(nattsv == 1, "变量属性数=1")

  call check(nf90_inquire_dimension(ncid, dimids(1), name=dname, len=dimlen) == NF90_NOERR, &
             "nf90_inquire_dimension")
  call check(trim(dname) == "x" .and. dimlen == NX, "维度 x 名称与长度一致")
  call check(nf90_get_att(ncid, varid, "units", units_out) == NF90_NOERR, "nf90_get_att units")
  call check(trim(units_out) == UNITS, "属性值一致")

  readback = -1.0d0
  call check(nf90_get_var(ncid, varid, readback) == NF90_NOERR, "nf90_get_var")
  call check(all(abs(readback - written) < 1.0d-12), "回读数据与写入逐元素一致")
  call check(nf90_close(ncid) == NF90_NOERR, "nf90_close（只读）")

  write(*, '(A,I0,A,I0,A)') "RESULT: netcdf-fortran consumer checks ", &
       checks - failures, "/", checks, " passed"
  if (failures /= 0) then
    write(*, '(A,I0)') "FAILURES: ", failures
    stop 1
  end if
  write(*, '(A)') "PASS: netcdf-fortran 消费者链路全通过"

contains

  subroutine check(cond, label)
    logical, intent(in) :: cond
    character(len=*), intent(in) :: label
    checks = checks + 1
    if (cond) then
      write(*, '(A,A)') "  [ok]   ", label
    else
      failures = failures + 1
      write(*, '(A,A)') "  [FAIL] ", label
    end if
  end subroutine check

end program test_netcdf_fortran
