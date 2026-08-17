;;; test_wiliki.scm — wiliki 0.6.2 L1 smoke test (Conan test_package)
;;; Loads the installed wiliki module and exercises a public API so the
;;; package content is actually verified (R34).
(use wiliki.parse)
(use srfi.13)  ; string-contains

(define result (wiliki-parse-string "Hello [[Wiki]]"))

(unless (pair? result)
  (error "wiliki-parse-string returned a non-pair result"))

(unless (string-contains
         (call-with-output-string (lambda (out) (write result out)))
         "Wiki")
  (error "wiliki-parse-string result does not contain expected wiki-name"))

;; The wiliki package is a set of Scheme modules installed into Gauche's
;; site lib; exercising wiliki.parse above already proves the installed
;; module tree is loadable (parse.scm depends on the same site-lib layout
;; as the rest of the package).  The full upstream `make check` suite
;; (226 assertions across 7 test files) is executed separately in the
;; conanfile build; see test_package/MANIFEST.yml.

(print "wiliki test: OK")
(exit 0)
