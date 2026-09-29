program test_libfdf
    use fdf, only: fdf_init, fdf_integer, fdf_physical, fdf_string, &
                   fdf_defined, fdf_shutdown
    use fdf_prec, only: dp
    implicit none

    integer :: atoms
    integer :: checks
    real(dp) :: cutoff
    character(len=32) :: name

    checks = 0
    call fdf_init('test.fdf', 'test.out')

    atoms = fdf_integer('NumberOfAtoms', 0)
    call check(atoms == 2, 'integer input')

    cutoff = fdf_physical('MeshCutoff', 0.0_dp, 'Ry')
    call check(abs(cutoff - 1.5_dp) < 1.0e-12_dp, 'physical units')

    name = fdf_string('NameOfFile', 'missing')
    call check(trim(name) == 'consumer test', 'string input')

    call check(fdf_defined('new-style'), 'defined marker')
    call fdf_shutdown()

    if (checks /= 4) then
        write (*, '(a,i0)') 'FAIL: unexpected check count ', checks
        error stop 1
    end if

    write (*, '(a,i0,a)') 'PASS: libfdf consumer API (', checks, ' checks)'

contains

    subroutine check(condition, label)
        logical, intent(in) :: condition
        character(len=*), intent(in) :: label

        checks = checks + 1
        if (.not. condition) then
            write (*, '(a,a)') 'FAIL: ', label
            error stop 1
        end if
    end subroutine check

end program test_libfdf
