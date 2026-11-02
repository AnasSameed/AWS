/*------------------------------------------------------------------
  ae_summary_export.sas - treatment-emergent AE summary, exported for the web
  Input : data/dm_raw.csv, data/ae_raw.csv   (synthetic)
  Output: output/ae_summary.csv   (same layout as python/build_report.py)
          output/ae_summary.html  (ODS HTML table, optional)

  Rules (identical to the Python builder):
   * Safety population = subjects with a first dose date and an arm of Placebo / Drug 10 mg
   * Treatment-emergent = AE start date on or after first dose date
   * A subject is counted once per preferred term
   * Percent = subjects with the event / safety subjects in that arm

  NOTE: written to match the Python version, which is unit-tested.
        This SAS code has NOT been run in SAS yet - run it, compare the CSV
        with site/ae_summary.csv, and fix any difference.
-------------------------------------------------------------------*/
%let root = /home/your_user/ae-report-s3;          /* <-- EDIT ME */
options dlcreatedir nodate nonumber;
libname outlib "&root./output";

/* 1. Read the raw files */
data dm;
  infile "&root./data/dm_raw.csv" dsd firstobs=2 truncover;
  length SUBJID $4 SITEID $3 RACE $40 SEX $1 ARM $20 CONSENTDT $10 FIRSTDOSE $10 LASTDOSE $10;
  input SUBJID $ SITEID $ AGE SEX $ RACE $ ARM $ CONSENTDT $ FIRSTDOSE $ LASTDOSE $;
  TRTSDT = input(FIRSTDOSE, ?? yymmdd10.);
  format TRTSDT date9.;
  if not missing(TRTSDT) and ARM in ("Placebo", "Drug 10 mg") then SAFFL = "Y";
  else SAFFL = "N";
run;

data ae;
  infile "&root./data/ae_raw.csv" dsd firstobs=2 truncover;
  length SUBJID $4 AETERM $60 AEBODSYS $60 AESEV $8 AESTDTC $10 AESER $1;
  input SUBJID $ AETERM $ AEBODSYS $ AESEV $ AESTDTC $ AESER $;
  AESTDT = input(AESTDTC, ?? yymmdd10.);
  format AESTDT date9.;
run;

/* 2. Treatment-emergent AEs in the safety population */
proc sql;
  create table teae as
  select a.AEBODSYS, a.AETERM, d.ARM, d.SUBJID
  from ae as a inner join dm as d on a.SUBJID = d.SUBJID
  where d.SAFFL = "Y" and a.AESTDT >= d.TRTSDT and not missing(a.AESTDT);

  create table denom as
  select ARM, count(distinct SUBJID) as bigN
  from dm where SAFFL = "Y" group by ARM;

  create table counts as
  select AEBODSYS, AETERM, ARM, count(distinct SUBJID) as n
  from teae group by AEBODSYS, AETERM, ARM;

  /* every term x arm combination, so a missing combination shows 0 */
  create table grid as
  select t.AEBODSYS, t.AETERM, d.ARM, d.bigN
  from (select distinct AEBODSYS, AETERM from counts) as t, denom as d;

  create table cells as
  select g.AEBODSYS, g.AETERM, g.ARM, g.bigN, coalesce(c.n, 0) as n
  from grid as g left join counts as c
       on g.AEBODSYS = c.AEBODSYS and g.AETERM = c.AETERM and g.ARM = c.ARM;
quit;

data cells;
  set cells;
  length cell $20;
  if n = 0 then cell = "0";
  else cell = cats(put(n, 3.), " (", put(100 * n / bigN, 5.1), "%)");
run;

proc sort data=cells; by AEBODSYS AETERM ARM; run;

proc transpose data=cells out=wide(drop=_name_) prefix=ARM_;
  by AEBODSYS AETERM;
  id ARM;
  var cell;
run;
/* column names after TRANSPOSE: ARM_Drug_10_mg and ARM_Placebo (VALIDVARNAME=V7 style) */

proc sql noprint;
  select bigN into :n_pbo trimmed from denom where ARM = "Placebo";
  select bigN into :n_trt trimmed from denom where ARM = "Drug 10 mg";
quit;

/* 3. Export the same CSV the website downloads */
data outlib.ae_summary;
  set wide;
  keep AEBODSYS AETERM ARM_Placebo ARM_Drug_10_mg;
  label AEBODSYS = "System Organ Class" AETERM = "Preferred Term"
        ARM_Placebo = "Placebo (N=&n_pbo.)" ARM_Drug_10_mg = "Drug 10 mg (N=&n_trt.)";
run;

proc export data=outlib.ae_summary outfile="&root./output/ae_summary.csv"
            dbms=csv replace label;
run;

/* 4. Optional: an HTML copy of the table straight from SAS */
ods html file="&root./output/ae_summary.html" style=htmlblue;
title "Subjects with Treatment-Emergent Adverse Events (Safety Population)";
title2 "Synthetic practice data";
proc print data=outlib.ae_summary label noobs; run;
ods html close;
title;
