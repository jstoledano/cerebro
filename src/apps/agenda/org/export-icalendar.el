;;; export-icalendar.el --- Export selected Org files to iCalendar -*- lexical-binding: t; -*-
;; Usage: emacs --batch -Q --script export-icalendar.el -- AGENDA_PATH OUTPUT_ICS FILE1.org [FILE2.org ...]

(require 'org)
(require 'org-agenda)
(require 'ox-icalendar)
(require 'cl-lib)
(require 'subr-x)

(defun agenda-icalendar-main ()
  (let ((args (cl-remove "--" command-line-args-left :test #'equal)))
    (unless (>= (length args) 3)
      (error "Usage: export-icalendar.el AGENDA_PATH OUTPUT_ICS FILE1.org [FILE2.org ...]"))
    (let* ((root (file-name-as-directory (expand-file-name (nth 0 args))))
           (output (expand-file-name (nth 1 args)))
           (relative-files (nthcdr 2 args))
           (files
            (mapcar
             (lambda (relative)
               (let ((file (expand-file-name relative root)))
                 (unless (and (string-suffix-p ".org" (downcase file))
                              (file-in-directory-p file root)
                              (file-regular-p file))
                   (error "Invalid or unavailable Org source: %s" relative))
                 file))
             relative-files)))
      (unless (file-directory-p root)
        (error "AGENDA_PATH is not a directory: %s" root))
      (let ((org-agenda-files files)
            (org-icalendar-combined-agenda-file output)
            (org-icalendar-include-todo t)
            (org-icalendar-store-UID nil)
            (org-icalendar-timezone "America/Mexico_City")
            (org-export-with-broken-links t))
        (org-icalendar-combine-agenda-files nil))
      (unless (file-exists-p output)
        (error "Org-mode did not create the ICS file: %s" output))
      (princ (format "Exported iCalendar from %d Org files to %s\n"
                     (length files) output)))))

(when noninteractive
  (condition-case err
      (agenda-icalendar-main)
    (error
     (princ (format "iCalendar export error: %s\n" (error-message-string err)))
     (kill-emacs 1))))

(provide 'export-icalendar)
;;; export-icalendar.el ends here
