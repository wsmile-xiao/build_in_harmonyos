:- initialization(main).

main :-
    X is 6 * 7,
    X =:= 42,
    writeln('trealla-consumer-ok'),
    halt.
