subroutine hello_sum(n, x, s)
  integer :: n, i
  double precision :: x(*), s
  s = 0.0d0
  do i = 1, n
    s = s + x(i)
  end do
end subroutine
