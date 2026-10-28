-- Synthetic clinical-trial mini database. Runs on MySQL 8 / Aurora MySQL and on SQLite.
-- No real patient data.
DROP TABLE IF EXISTS adverse_events;
DROP TABLE IF EXISTS visits;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS sites;

CREATE TABLE sites (
  site_id    INTEGER PRIMARY KEY,
  site_name  VARCHAR(50) NOT NULL,
  country    VARCHAR(30) NOT NULL
);

CREATE TABLE subjects (
  subject_id INTEGER PRIMARY KEY,
  site_id    INTEGER NOT NULL,
  age        INTEGER NOT NULL CHECK (age BETWEEN 18 AND 90),
  sex        CHAR(1) NOT NULL CHECK (sex IN ('M','F')),
  arm        VARCHAR(20) NOT NULL,           -- Placebo / Drug 10 mg
  FOREIGN KEY (site_id) REFERENCES sites(site_id)
);

CREATE TABLE visits (
  visit_id   INTEGER PRIMARY KEY,
  subject_id INTEGER NOT NULL,
  visit_no   INTEGER NOT NULL,
  visit_date DATE NOT NULL,
  sys_bp     INTEGER,                        -- systolic blood pressure
  FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

CREATE TABLE adverse_events (
  ae_id      INTEGER PRIMARY KEY,
  subject_id INTEGER NOT NULL,
  ae_term    VARCHAR(40) NOT NULL,
  severity   VARCHAR(10) NOT NULL CHECK (severity IN ('MILD','MODERATE','SEVERE')),
  start_date DATE NOT NULL,
  FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

CREATE INDEX idx_visits_subject ON visits(subject_id);
CREATE INDEX idx_ae_subject     ON adverse_events(subject_id);
