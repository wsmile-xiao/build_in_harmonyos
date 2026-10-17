program test_mbd
use mbd_constants
use mbd, only: mbd_input_t, mbd_calc_t
implicit none
integer :: n_pass
n_pass = 0
call check_energy(n_pass)
call check_gradients(n_pass)
call check_energy_from_ratios(n_pass)
if (n_pass /= 3) then
    print *, 'MBD_TEST_FAIL: ', n_pass, '/3'
    stop 1
end if
print *, 'MBD_TEST_ALL_PASS: 3/3'

contains

subroutine check_energy(n_pass)
    integer, intent(inout) :: n_pass
    type(mbd_input_t) :: inp
    type(mbd_calc_t) :: calc
    real(dp) :: energy
    inp%atom_types = ['Ar', 'Ar']
    inp%coords = reshape([0d0, 0d0, 0d0, 0d0, 0d0, 4d0*ang], [3, 2])
    inp%xc = 'pbe'
    call calc%init(inp)
    call calc%update_vdw_params_custom([11d0, 11d0], [63.525d0, 63.525d0], [3.55d0, 3.55d0])
    call calc%evaluate_vdw_method(energy)
    call calc%destroy()
    if (abs((energy + 2.4329456747018696d-4)/2.4329456747018696d-4) < 1d-6) then
        print *, 'MBD_TEST_PASS: energy =', energy
        n_pass = n_pass + 1
    else
        print *, 'MBD_TEST_FAIL: energy =', energy
        stop 1
    end if
end subroutine

subroutine check_gradients(n_pass)
    integer, intent(inout) :: n_pass
    type(mbd_input_t) :: inp
    type(mbd_calc_t) :: calc
    real(dp) :: energy
    real(dp), allocatable :: gradients(:, :)
    inp%atom_types = ['Ar', 'Ar']
    inp%coords = reshape([0d0, 0d0, 0d0, 0d0, 0d0, 4d0*ang], [3, 2])
    inp%xc = 'pbe'
    call calc%init(inp)
    call calc%update_vdw_params_custom([11d0, 11d0], [63.525d0, 63.525d0], [3.55d0, 3.55d0])
    call calc%evaluate_vdw_method(energy)
    allocate (gradients(3, 2))
    call calc%get_gradients(gradients)
    call calc%destroy()
    if (abs((sum(abs(gradients)) - 2.3279742219399908d-4)/2.3279742219399908d-4) < 1d-6) then
        print *, 'MBD_TEST_PASS: gradients =', sum(abs(gradients))
        n_pass = n_pass + 1
    else
        print *, 'MBD_TEST_FAIL: gradients =', sum(abs(gradients))
        stop 1
    end if
end subroutine

subroutine check_energy_from_ratios(n_pass)
    integer, intent(inout) :: n_pass
    type(mbd_input_t) :: inp
    type(mbd_calc_t) :: calc
    real(dp) :: energy
    inp%atom_types = ['Ar', 'Ar']
    inp%coords = reshape([0d0, 0d0, 0d0, 0d0, 0d0, 4d0*ang], [3, 2])
    inp%xc = 'pbe'
    call calc%init(inp)
    call calc%update_vdw_params_from_ratios([1d0, 1d0])
    call calc%evaluate_vdw_method(energy)
    call calc%destroy()
    if (abs((energy + 0.0002462647623815428d0)/0.0002462647623815428d0) < 1d-6) then
        print *, 'MBD_TEST_PASS: energy_from_ratios =', energy
        n_pass = n_pass + 1
    else
        print *, 'MBD_TEST_FAIL: energy_from_ratios =', energy
        stop 1
    end if
end subroutine

end program
