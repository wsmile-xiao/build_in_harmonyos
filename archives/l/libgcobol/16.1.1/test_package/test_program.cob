       IDENTIFICATION DIVISION.
       PROGRAM-ID. LIBGCOBOL-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 RESULT      PIC 9(10)  VALUE 0.
       01 R-FIXED     PIC 99V99  VALUE 0.
       01 STR-BUF     PIC X(20)  VALUE SPACES.
       01 I           PIC 99     VALUE 0.
       01 TOTAL       PIC 999    VALUE 0.
       PROCEDURE DIVISION.
       MAIN.
           COMPUTE RESULT = 10 ** 2
           DISPLAY "POWER:" RESULT
           COMPUTE R-FIXED = 3.5 * 2
           DISPLAY "FIXED:" R-FIXED
           MOVE "HELLO-LIBGCOBOL" TO STR-BUF
           DISPLAY "STR:" STR-BUF
           IF RESULT = 100
               DISPLAY "IF:OK"
           ELSE
               DISPLAY "IF:FAIL"
           END-IF
           PERFORM VARYING I FROM 1 BY 1 UNTIL I > 5
               ADD I TO TOTAL
           END-PERFORM
           DISPLAY "SUM1-5:" TOTAL
           DISPLAY "MAX:" FUNCTION MAX(3 -14 0 8 -3)
           DISPLAY "MIN:" FUNCTION MIN(3 -14 0 8 -3)
           STOP RUN.
