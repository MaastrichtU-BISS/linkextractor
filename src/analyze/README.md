# Reanalze

The purpose of this subproject of linkextractor-lite is to go through all caselaw texts and attempt to extract references using the linkextractor-lite logic. The extracted links will be compared to the links in the database, originating from LIDO. First, mostly manual analysis will be done to check whether we're extracting references that were not considered by LIDO, or whether LIDO has references that we are not considering.

## Strategy

1. Acquire test/sample subset of cases and full-texts from the live db
2. Perform automatic extraction on this subset
3. Compare results with LIDO 'ground-truth' of references.
    - References that LIDO detects but we don't: False Negatives
    - References that we detect but LIDO doens't: True Positives
4. Manuall check if there are references in texts that were uncaught
    - References that we manually detect but the extractor doesn't: False Negatives
    - References that were extracted, but upon manual inspection seem to be wrong: False Positives
5. From acquired knowlegde, update extraction logic and repeat step 2-4
6. Run on complete set and compare amount of references that were caught against LIDO to compute meaningful metrics
