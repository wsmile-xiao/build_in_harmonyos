program test_fortran_shlex
    use shlex_module, only: shlex_token, split, shlex, ms_split, ms_quote
    implicit none

    character(len=:), allocatable :: words(:)
    character(len=:), allocatable :: windows_words(:)
    character(len=:), allocatable :: roundtrip(:)
    character(len=:), allocatable :: quoted
    type(shlex_token), allocatable :: tokens(:)
    logical :: ok
    integer :: checks

    checks = 0

    words = split('compiler -I /sdk/include "two words"', success=ok)
    call check(ok, "POSIX split reports success")
    call check(size(words) == 4, "POSIX split returns four words")
    if (size(words) == 4) then
        call check(trim(words(1)) == "compiler", "POSIX word 1")
        call check(trim(words(2)) == "-I", "POSIX word 2")
        call check(trim(words(3)) == "/sdk/include", "POSIX word 3")
        call check(trim(words(4)) == "two words", "POSIX quoted word")
    end if

    words = split( &
        'compiler -I /sdk/include -L /sdk/lib', &
        join_spaced=.true., &
        keep_quotes=.false., &
        success=ok &
    )
    call check(ok, "joined split reports success")
    call check(size(words) == 3, "joined split returns three words")
    if (size(words) == 3) then
        call check(trim(words(1)) == "compiler", "joined word 1")
        call check(trim(words(2)) == "-I/sdk/include", "joined include flag")
        call check(trim(words(3)) == "-L/sdk/lib", "joined library flag")
    end if

    tokens = shlex("'alpha beta' gamma", success=ok, keep_quotes=.false.)
    call check(ok, "structured shlex reports success")
    call check(size(tokens) == 2, "structured shlex returns two tokens")
    if (size(tokens) == 2) then
        call check(trim(tokens(1)%string) == "alpha beta", "structured token 1")
        call check(trim(tokens(2)%string) == "gamma", "structured token 2")
    end if

    windows_words = ms_split( &
        '"my file.txt" -DVALUE=42', &
        like_cmd=.true., &
        ucrt=.true., &
        success=ok &
    )
    call check(ok, "Windows split reports success")
    call check(size(windows_words) == 2, "Windows split returns two words")
    if (size(windows_words) == 2) then
        call check(trim(windows_words(1)) == "my file.txt", "Windows quoted word")
        call check(trim(windows_words(2)) == "-DVALUE=42", "Windows flag")
    end if

    quoted = ms_quote("my file.txt", for_cmd=.false.)
    call check(quoted == '"my file.txt"', "Windows direct quoting")

    roundtrip = ms_split( &
        quoted, &
        like_cmd=.false., &
        ucrt=.true., &
        success=ok &
    )
    call check(ok, "Windows quote round-trip reports success")
    call check(size(roundtrip) == 1, "Windows quote round-trip size")
    if (size(roundtrip) == 1) then
        call check(trim(roundtrip(1)) == "my file.txt", "Windows quote round-trip value")
    end if

    if (checks /= 23) then
        write (*, '(a,i0)') "FAIL: unexpected check count ", checks
        error stop 1
    end if

    write (*, '(a,i0,a)') "PASS: fortran-shlex consumer API (", checks, " checks)"

contains

    subroutine check(condition, label)
        logical, intent(in) :: condition
        character(len=*), intent(in) :: label

        checks = checks + 1
        if (.not. condition) then
            write (*, '(a,a)') "FAIL: ", label
            error stop 1
        end if
    end subroutine check

end program test_fortran_shlex
