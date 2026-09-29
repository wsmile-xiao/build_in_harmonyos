{ fpc/3.2.2 test_package: minimal upstream-style Pascal program. }
program hello;

var
  i: Integer;
  total: Integer;
begin
  total := 0;
  for i := 1 to 42 do
    total := total + i;
  WriteLn('hello from fpc on ', {$I %FPCTARGETOS%}, '/', {$I %FPCTARGETCPU%}, ' = ', total);
end.
