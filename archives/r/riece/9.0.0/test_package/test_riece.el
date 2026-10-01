;;; test_riece.el --- Consumer load test for riece -*- lexical-binding: t; -*-

;; 1. riece must resolve from the packaged lisp directory.
(let ((library (locate-library "riece")))
  (unless (and (stringp library)
               (string-match-p "riece/riece\\.elc?\\'" library))
    (error "riece library was not loaded from the packaged lisp dir: %S" library)))

;; 2. The package loads and reports the expected upstream version.
(require 'riece)
(unless (featurep 'riece)
  (error "riece feature was not provided"))

(require 'riece-version)
(unless (equal riece-version-number "9.0.0")
  (error "unexpected riece version: %S" riece-version-number))

;; 3. GNU Emacs 29 make-face adaptation (platform case).
;;    Upstream riece calls the single-argument GNU Emacs 29 make-face with an
;;    extra XEmacs-style docstring in three isomorphic top-level blocks
;;    (riece-highlight.el, riece-history.el, riece-unread.el).  Every one of
;;    them aborts its module load on Emacs 29, so load all three and assert both
;;    the faces and their documentation survive.
(dolist (pair '((riece-highlight . riece-modeline-current-face)
                (riece-history   . riece-modeline-history-face)
                (riece-unread    . riece-modeline-unread-face)))
  (require (car pair))
  (unless (featurep (car pair))
    (error "%s feature was not provided" (car pair)))
  (unless (facep (cdr pair))
    (error "%s was not defined" (cdr pair)))
  (unless (get (cdr pair) 'face-documentation)
    (error "%s lost its face-documentation" (cdr pair))))

;; 4. End-to-end startup path: riece.el's `riece' entry point resolves the
;;    default addon list, which loads riece-unread / riece-history (the two
;;    previously broken sites).  Mirror that call to prove `M-x riece' works.
(require 'riece-addon)
(setq riece-addon-dependencies (riece-resolve-addons (copy-sequence riece-addons)))
(unless (>= (length riece-addon-dependencies) 17)
  (error "default addon resolution is incomplete: %S"
         (length riece-addon-dependencies)))

(message "riece consumer load validation OK")

;;; test_riece.el ends here
