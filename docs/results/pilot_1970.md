# LTE FALCON session: pilot_1970

Decoded DCI log summary for **1970 MHz**.

- Valid records: 198; invalid rows: 9 (schema errors: 1).
- Timestamp span: 120.542 seconds, from 1792351007.062030 to 1792351127.603714.
- Total observed PRB assignments: 4042; DCI records: 198.
- Distinct observed nonreserved RNTIs: 45. This excludes RNTI 0 and identifiers >=65524, is approximate with respect to reserved identifier usage, and does not classify or count all C-RNTIs, devices, or users.

Missing activity windows have no CSV row and are shown as gaps in the chart. PRB assignments are observed decoded grant allocations, not utilization, throughput, congestion, or delivered traffic.

## Figures and data

- Activity: [activity.svg](../../figures/pilot_1970/activity.svg)
- MCS distribution: [mcs.svg](../../figures/pilot_1970/mcs.svg). MCS labels are counts of decoded records, not direct channel-quality measurements.
- Window aggregates: [activity.csv](../../data/processed/pilot_1970/activity.csv)
- MCS counts: [mcs_distribution.csv](../../data/processed/pilot_1970/mcs_distribution.csv)

## Synthetic record-removal sensitivity experiment

A fixed-seed Bernoulli experiment removes decoded records at the listed rates and compares total PRB assignments with the baseline. This is synthetic missing decoded records, not real subframes, an RF model, or an anomaly detector. Results use one seed and are exploratory, not an accuracy estimate.
- [Synthetic record-removal chart](../../figures/pilot_1970/synthetic_record_removal.svg)
- [Synthetic record-removal values](../../data/processed/pilot_1970/synthetic_record_removal.csv)

## Capture notes

Input parsing counted 0 comment lines and 0 blank lines.
No recognized skipped-subframe summary was supplied from the console.
