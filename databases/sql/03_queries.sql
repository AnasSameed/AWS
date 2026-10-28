-- Practice queries. Read the comment, guess the result, then run it.

-- 1. Subjects per arm
SELECT arm, COUNT(*) AS n FROM subjects GROUP BY arm;

-- 2. JOIN: subjects with their site name
SELECT s.subject_id, s.arm, st.site_name
FROM subjects s JOIN sites st ON st.site_id = s.site_id
ORDER BY s.subject_id LIMIT 5;

-- 3. Average systolic BP by arm and visit (the "treatment effect" view)
SELECT s.arm, v.visit_no, ROUND(AVG(v.sys_bp),1) AS avg_sys_bp
FROM visits v JOIN subjects s ON s.subject_id = v.subject_id
GROUP BY s.arm, v.visit_no
ORDER BY s.arm, v.visit_no;

-- 4. Adverse events per arm, split by severity
SELECT s.arm, a.severity, COUNT(*) AS n_events
FROM adverse_events a JOIN subjects s ON s.subject_id = a.subject_id
GROUP BY s.arm, a.severity
ORDER BY s.arm, a.severity;

-- 5. LEFT JOIN: subjects with NO adverse events (INNER JOIN would hide them)
SELECT s.subject_id, s.arm
FROM subjects s LEFT JOIN adverse_events a ON a.subject_id = s.subject_id
WHERE a.ae_id IS NULL
ORDER BY s.subject_id;

-- 6. HAVING: subjects with 2 or more adverse events
SELECT subject_id, COUNT(*) AS n_ae
FROM adverse_events GROUP BY subject_id HAVING COUNT(*) >= 2
ORDER BY n_ae DESC, subject_id;

-- 7. Window function: change in BP from the first visit for each subject
SELECT subject_id, visit_no, sys_bp,
       sys_bp - FIRST_VALUE(sys_bp) OVER (PARTITION BY subject_id ORDER BY visit_no) AS change_from_baseline
FROM visits
WHERE subject_id <= 3
ORDER BY subject_id, visit_no;

-- 8. Constraint test: this MUST fail (age 12 violates the CHECK, if your engine enforces it)
-- INSERT INTO subjects VALUES (99,1,12,'M','Placebo');

-- 9. On Aurora/MySQL only: see how a query is executed, and which index it uses
-- EXPLAIN SELECT * FROM visits WHERE subject_id = 5;
