;;; test_notmuch_emacs.el --- Consumer load test for notmuch-emacs -*- lexical-binding: t; -*-

(defun test-notmuch-emacs--packaged-library-p (library basename)
  (and (stringp library)
       (string-match-p
        (concat "notmuch-0\\.40/" (regexp-quote basename) "\\.elc?\\'")
        library)))

(let ((library (locate-library "notmuch-lib")))
  (unless (test-notmuch-emacs--packaged-library-p library "notmuch-lib")
    (error "notmuch-lib was not loaded from the packaged lisp dir: %S" library)))

(let ((library (locate-library "notmuch")))
  (unless (test-notmuch-emacs--packaged-library-p library "notmuch")
    (error "notmuch library was not loaded from the packaged lisp dir: %S" library)))

(require 'notmuch-version)
(require 'notmuch-lib)
(require 'notmuch)

(unless (string= notmuch-emacs-version "0.40")
  (error "unexpected notmuch-emacs-version: %S" notmuch-emacs-version))

(unless (featurep 'notmuch-lib)
  (error "notmuch-lib feature was not provided"))

(unless (featurep 'notmuch)
  (error "notmuch feature was not provided"))

(unless (fboundp 'notmuch)
  (error "notmuch command entry point is not defined"))

(unless (fboundp 'notmuch-search)
  (error "notmuch-search entry point is not defined"))

(message "notmuch-emacs consumer load validation OK")

;;; test_notmuch_emacs.el ends here
