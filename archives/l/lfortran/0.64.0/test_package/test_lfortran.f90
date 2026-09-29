program test_lfortran
    use iso_fortran_env, only: real64
    implicit none
    real(real64) :: x, y
    real(real64) :: arr(4)
    integer :: i, s
    character(len=:), allocatable :: msg

    ! 内建数学函数（走 lfortran 运行时 intrinsic）
    x = sin(0.0_real64) + cos(0.0_real64)   ! == 1.0
    y = sqrt(4.0_real64)                    ! == 2.0
    if (abs(x - 1.0_real64) > 1.0e-12_real64) error stop 1
    if (abs(y - 2.0_real64) > 1.0e-12_real64) error stop 2

    ! 数组运算 + sum intrinsic
    arr = [1.0_real64, 2.0_real64, 3.0_real64, 4.0_real64]
    if (abs(sum(arr) - 10.0_real64) > 1.0e-12_real64) error stop 3

    ! do 循环累加
    s = 0
    do i = 1, 100
        s = s + i
    end do
    if (s /= 5050) error stop 4

    ! 字符串：trim/adjustl + 分配式长度字符（trim 只去尾随空格，
    ! 前导空格须 adjustl 先移后，否则前导空格保留）
    msg = trim(adjustl("  hello lfortran  "))
    if (msg /= "hello lfortran") error stop 5
    if (len(msg) /= 14) error stop 6

    print '(A)', "ALL_OK"
end program
