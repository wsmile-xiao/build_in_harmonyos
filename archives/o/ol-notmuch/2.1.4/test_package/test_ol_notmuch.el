;;; test_ol_notmuch.el --- Consumer load test for ol-notmuch -*- lexical-binding: t; -*-

(defun test-ol-notmuch--packaged-library-p (library directory basename)
  (and (stringp library)
       (string-match-p
        (concat (regexp-quote directory)
                "/"
                (regexp-quote basename)
                "\\.elc?\\'")
        library)))

(let ((library (locate-library "compat")))
  (unless (test-ol-notmuch--packaged-library-p library "compat-31.0.0.2" "compat")
    (error "compat was not loaded from the packaged lisp dir: %S" library)))

(let ((library (locate-library "ol")))
  (unless (test-ol-notmuch--packaged-library-p library "org-9.8.8" "ol")
    (error "ol was not loaded from the packaged org lisp dir: %S" library)))

(let ((library (locate-library "notmuch")))
  (unless (test-ol-notmuch--packaged-library-p library "notmuch-0.40" "notmuch")
    (error "notmuch was not loaded from the packaged lisp dir: %S" library)))

(let ((library (locate-library "ol-notmuch")))
  (unless (test-ol-notmuch--packaged-library-p library "ol-notmuch-2.1.4" "ol-notmuch")
    (error "ol-notmuch was not loaded from the packaged lisp dir: %S" library)))

(require 'org)
(require 'compat)
(require 'notmuch)
(require 'ol-notmuch)

(dolist (feature '(compat notmuch ol-notmuch))
  (unless (featurep feature)
    (error "%S feature was not provided" feature)))

(dolist (function '(org-notmuch-open
                    org-notmuch-follow-link
                    org-notmuch-search-open
                    org-notmuch-tree-open))
  (unless (fboundp function)
    (error "%S entry point is not defined" function)))

(dolist (link-type '("notmuch" "notmuch-search" "notmuch-tree"))
  (unless (assoc link-type org-link-parameters)
    (error "%S link parameters were not registered" link-type)))

(message "ol-notmuch consumer load validation OK")

;;; test_ol_notmuch.el ends here
