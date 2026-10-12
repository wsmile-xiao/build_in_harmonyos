program test_libpsml_consumer
  ! Consumer test for the packaged libpsml (links libpsml.a + libxmlf90.a,
  ! imports the packaged m_psml module file, parses a verbatim upstream
  ! fixture and exercises the reader error path). Four real checks; the
  ! single deterministic summary line is the count source for the
  ! HMBS_TEST_PACKAGE_RESULT marker (no stdout word counting).
  use m_psml
  implicit none

  type(ps_t) :: ps, ps2
  real(kind=ps_real_kind) :: atnum
  character(len=16) :: symbol
  character(len=1024) :: fixture
  integer :: st, st2, passed, total, narg

  total = 4
  passed = 0

  narg = command_argument_count()
  if (narg >= 1) then
    call get_command_argument(1, fixture)
  else
    fixture = "14_Si.psml"
  end if

  ! CHECK 1: parse the upstream Si fixture (end-to-end reader path).
  call psml_reader(trim(fixture), ps, stat=st)
  if (st == 0) then
    passed = passed + 1
    print *, "CHECK 1 PASSED: psml_reader parsed ", trim(fixture)
  else
    print *, "CHECK 1 FAILED: psml_reader stat=", st
  end if

  if (st == 0) then
    ! CHECK 2: atomic number of Si is 14 (same assertion as upstream getz).
    call ps_PseudoAtomSpec_Get(ps, atomic_number=atnum)
    if (int(atnum) == 14) then
      passed = passed + 1
      print *, "CHECK 2 PASSED: atomic_number=14"
    else
      print *, "CHECK 2 FAILED: atomic_number=", atnum
    end if

    ! CHECK 3: atomic symbol is Si.
    call ps_PseudoAtomSpec_Get(ps, atomic_symbol=symbol)
    if (trim(symbol) == "Si") then
      passed = passed + 1
      print *, "CHECK 3 PASSED: atomic_symbol=Si"
    else
      print *, "CHECK 3 FAILED: atomic_symbol=", trim(symbol)
    end if
  else
    print *, "CHECK 2 FAILED: skipped (fixture did not parse)"
    print *, "CHECK 3 FAILED: skipped (fixture did not parse)"
  end if

  ! CHECK 4: missing file must return non-zero stat (upstream getz_stat
  ! error path), not die.
  call psml_reader("libpsml-consumer-does-not-exist.psml", ps2, stat=st2)
  if (st2 /= 0) then
    passed = passed + 1
    print *, "CHECK 4 PASSED: missing file stat=", st2
  else
    print *, "CHECK 4 FAILED: missing file returned stat=0"
  end if

  write(*, '("LIBPSML_CONSUMER ", I0, "/", I0, " CHECKS PASSED")') passed, total
  if (passed /= total) stop 1

end program test_libpsml_consumer
