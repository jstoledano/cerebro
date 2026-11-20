;;; export-agenda.el --- Export selected Org files to JSON -*- lexical-binding: t; -*-
;; Usage: emacs --batch -Q --script export-agenda.el -- AGENDA_PATH OUTPUT_JSON FILE1.org [FILE2.org ...]

(require 'cl-lib)
(require 'json)
(require 'org)
(require 'org-element)
(require 'subr-x)

(defconst agenda-export-schema-version 1)

(defun agenda-export--obj (&rest pairs)
  (let ((obj (make-hash-table :test 'equal)))
    (while pairs (puthash (pop pairs) (pop pairs) obj))
    obj))

(defun agenda-export--iso (year month day &optional hour minute)
  (when (and year month day)
    (if (numberp hour)
        (format "%04d-%02d-%02dT%02d:%02d" year month day hour (or minute 0))
      (format "%04d-%02d-%02d" year month day))))

(defun agenda-export--timestamp (timestamp)
  (when timestamp
    (let* ((year (org-element-property :year-start timestamp))
           (month (org-element-property :month-start timestamp))
           (day (org-element-property :day-start timestamp))
           (hour (org-element-property :hour-start timestamp))
           (minute (org-element-property :minute-start timestamp))
           (end-year (org-element-property :year-end timestamp))
           (end-month (org-element-property :month-end timestamp))
           (end-day (org-element-property :day-end timestamp))
           (end-hour (org-element-property :hour-end timestamp))
           (end-minute (org-element-property :minute-end timestamp))
           (repeater-type (org-element-property :repeater-type timestamp))
           (repeater-value (org-element-property :repeater-value timestamp))
           (repeater-unit (org-element-property :repeater-unit timestamp))
           (repeater-prefix (pcase repeater-type
                              ('cumulate "+") ('catch-up "++") ('restart ".+") (_ "")))
           (repeater-raw (when (and repeater-type repeater-value repeater-unit)
                           (format "%s%d%s" repeater-prefix repeater-value repeater-unit))))
      (agenda-export--obj
       "raw" (org-element-property :raw-value timestamp)
       "start" (agenda-export--iso year month day hour minute)
       "end" (agenda-export--iso end-year end-month end-day end-hour end-minute)
       "repeater" (when repeater-type
                    (agenda-export--obj
                     "type" (format "%s" repeater-type)
                     "value" repeater-value
                     "unit" (and repeater-unit (format "%s" repeater-unit))
                     "raw" repeater-raw))))))

(defun agenda-export--properties (headline)
  "Return only explicitly stored drawer properties for HEADLINE."
  (let ((properties (make-hash-table :test 'equal))
        (drawer (org-element-map headline 'property-drawer #'identity nil t t)))
    (when drawer
      (org-element-map
          drawer 'node-property
        (lambda (node)
          (let ((key (org-element-property :key node))
                (value (org-element-property :value node)))
            (when (and (stringp key) (stringp value))
              (puthash (upcase key) value properties))))))
    properties))

(defun agenda-export--outline (headline)
  (let ((parent (org-element-property :parent headline)) result)
    (while (and parent (eq (org-element-type parent) 'headline))
      (push (org-element-property :raw-value parent) result)
      (setq parent (org-element-property :parent parent)))
    (vconcat result)))

(defun agenda-export--body (headline)
  (let ((section (org-element-map headline 'section #'identity nil t t)))
    (if (not section) ""
      (let ((parts
             (cl-remove-if
              (lambda (element)
                (or (memq (org-element-type element) '(planning property-drawer))
                    (and (eq (org-element-type element) 'drawer)
                         (member (upcase (or (org-element-property :drawer-name element) ""))
                                 '("PROPERTIES" "LOGBOOK")))))
              (org-element-contents section))))
        (string-trim (mapconcat #'org-element-interpret-data parts ""))))))

(defun agenda-export--timestamps (headline)
  (let (items)
    (org-element-map headline 'timestamp
      (lambda (timestamp)
        (let ((value (agenda-export--timestamp timestamp)))
          (when value (push value items))))
      nil nil t)
    (vconcat (nreverse items))))

(defun agenda-export--headline (headline source)
  (let* ((position (org-element-property :begin headline))
         (todo (org-element-property :todo-keyword headline))
         (scheduled (org-element-property :scheduled headline))
         (deadline (org-element-property :deadline headline))
         (closed (org-element-property :closed headline))
         (timestamps (agenda-export--timestamps headline))
         (tags (org-element-property :tags headline))
         (cookie-priority (org-element-property :priority headline))
         (properties (agenda-export--properties headline))
         (priority (or (and cookie-priority (char-to-string cookie-priority))
                       (gethash "PRIORITY" properties))))
    (when (or todo scheduled deadline (> (length timestamps) 0))
      (agenda-export--obj
       "kind" (if todo "task" "event")
       "id" (org-entry-get position "ID")
       "title" (org-element-property :raw-value headline)
       "state" todo
       "todo_type" (let ((type (org-element-property :todo-type headline)))
                     (and type (format "%s" type)))
       "priority" priority
       "tags" (vconcat (or tags nil))
       "source" source
       "line" (line-number-at-pos position)
       "level" (org-element-property :level headline)
       "outline" (agenda-export--outline headline)
       "scheduled" (agenda-export--timestamp scheduled)
       "deadline" (agenda-export--timestamp deadline)
       "closed" (agenda-export--timestamp closed)
       "timestamps" timestamps
       "properties" properties
       "body" (agenda-export--body headline)))))

(defun agenda-export--read-file (file root)
  (with-temp-buffer
    (insert-file-contents file)
    (org-mode)
    (let ((tree (org-element-parse-buffer))
          (relative (file-relative-name file root))
          items)
      (org-element-map tree 'headline
        (lambda (headline)
          (let ((item (agenda-export--headline headline relative)))
            (when item (push item items)))))
      (nreverse items))))

(defun agenda-export--validate (items)
  (let ((ids (make-hash-table :test 'equal)) missing)
    (dolist (item items)
      (when (equal (gethash "kind" item) "task")
        (let ((id (gethash "id" item))
              (reference (agenda-export--obj
                          "source" (gethash "source" item)
                          "line" (gethash "line" item)
                          "title" (gethash "title" item))))
          (if (string-empty-p (or id ""))
              (push reference missing)
            (puthash id (cons reference (gethash id ids)) ids)))))
    (let ((duplicates (make-hash-table :test 'equal)))
      (maphash (lambda (id references)
                 (when (> (length references) 1)
                   (puthash id (vconcat (nreverse references)) duplicates))) ids)
      (agenda-export--obj
       "valid" (and (null missing) (= (hash-table-count duplicates) 0))
       "missing_ids" (vconcat (nreverse missing))
       "duplicate_ids" duplicates))))

(defun agenda-export--selected-files (root relative-files)
  (unless relative-files (error "No se especificaron archivos Org autorizados"))
  (mapcar
   (lambda (relative)
     (let ((file (expand-file-name relative root)))
       (unless (and (string-suffix-p ".org" (downcase file))
                    (file-in-directory-p file root)
                    (file-regular-p file))
         (error "Archivo Org no valido o inexistente: %s" relative))
       file))
   relative-files))

(defun agenda-export-run (agenda-dir output-file relative-files)
  (let* ((root (file-name-as-directory (expand-file-name agenda-dir)))
         (_ (unless (file-directory-p root) (error "AGENDA_PATH no existe: %s" root)))
         (files (agenda-export--selected-files root relative-files))
         (items nil) sources)
    (dolist (file files)
      (push (file-relative-name file root) sources)
      (setq items (nconc items (agenda-export--read-file file root))))
    (setq sources (nreverse sources))
    (let* ((validation (agenda-export--validate items))
           (data (agenda-export--obj
                  "schema_version" agenda-export-schema-version
                  "generated_at" (format-time-string "%Y-%m-%dT%H:%M:%S%z")
                  "agenda_path" root
                  "source_files" (vconcat sources)
                  "item_count" (length items)
                  "task_count" (cl-count "task" items :key (lambda (item) (gethash "kind" item)) :test #'equal)
                  "event_count" (cl-count "event" items :key (lambda (item) (gethash "kind" item)) :test #'equal)
                  "items" (vconcat items)
                  "validation" validation)))
      (let ((json-encoding-pretty-print t) (coding-system-for-write 'utf-8-unix))
        (with-temp-file output-file
          (insert (json-encode data))
          (insert "\n")))
      (princ (format "Exported %d items from %d Org files to %s\n"
                     (length items) (length files) output-file))
      (unless (gethash "valid" validation)
        (princ "WARNING: task IDs are missing or duplicated. See validation in JSON.\n"))
      data)))

(defun agenda-export-main ()
  (let ((arguments (cl-remove "--" command-line-args-left :test #'equal)))
    (unless (>= (length arguments) 3)
      (error "Usage: export-agenda.el AGENDA_PATH OUTPUT_JSON FILE1.org [FILE2.org ...]"))
    (agenda-export-run (nth 0 arguments) (nth 1 arguments) (nthcdr 2 arguments))))

(when noninteractive
  (condition-case error-data
      (agenda-export-main)
    (error
     (princ (format "agenda export error: %s\n" (error-message-string error-data)))
     (kill-emacs 1))))

(provide 'export-agenda)
;;; export-agenda.el ends here
