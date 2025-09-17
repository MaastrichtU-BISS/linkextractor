# Reanalze

The purpose of this subproject of linkextractor-lite is to go through all caselaw texts and attempt to extract references using the linkextractor-lite logic. The extracted links will be compared to the links in the database, originating from LIDO. First, mostly manual analysis will be done to check whether we're extracting references that were not considered by LIDO, or whether LIDO has references that we are not considering.

## Method

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

### Interpreting results

First, after running the preperation of the analysis (-p), two files will be generated: `links_lido.json` and `full_text.txt`.
After running the analysis two additional files will be generated: `links_custom.json` and `analysis.json`.
In the terminal window, it should be clear to see where to investigate.

The perfect case would be for each case having a value of 0 for `FN`, maybe some values for `FN`. 

**If `FN` is non-zero for a case** \
This could mean two things:
- We did not capture a correct link that lido did match,
- Lido *incorrectly* considered a string as a link (unlikely)

The way to go about this, is look in the `analysis.json` where the `FN` values come from. The easiest is copying the `title` or `bwb_label_id` and looking up that value in the respective `links_lido.json` (since that file has the link, while the other doesn't). Then, one can proceed to analyze why this piece of text was considered a link in one parser and not in the other.

**If `FP` is non-zero for a case** \
This could mean two things:
- We captured a link that lido did not match,
- We *incorrectly* considered a string as a link

The operation to investigate this case is the equivalent of the above case, but the other way around: first look at the `FP` section of the `analysis.json` and then cross-reference those results in the `links_custom.json`.

## Results

In this paragraph, misclassifications will be indentified.

### False Positives

These links are links we recognized but are not recognized by lido. Either because:
- we incorrectly indentified them as links or identified them as the wrong link, or
- we correctly identified them as a link, while lido missed it (here the real gains can be achieved)

**1. ambiguous aliases**

Rv

**2. Unique opschrifts**

It seems that the links of lido are unique by opschrifts. Meaning, if there are multiple occurances of the same opschrift, they will be noted as (an amount) of 1. 
To equalize the results between lido and custom, we therefore have to ensure that custom also groups by opschrift (`context->literal`) to ensure we don't falsely flag these as FP.
Do note that custom also takes into account the spans, and for the analysis ensures that each span is only considered as a unique result.

Example 1, case ECLI:NL:HR:2022:380:
Here "art. 3 Wbbbg" occurs three times in the full-text. However, it is only listed once in the links of lido. 
In custom, these are caught as three individual links, distinguished by the unique span.

**Solution**:
Deduplicate the custom links before passing to the comparison function, to ensure same results.

### False Negatives

These are links that the custom link-extractor did not recognize.

**1. Conjunctions**

In some cases, there are multiple references conjoined in a single match/string. For example, having the literal "artiekelen" followed by a list of comma-seperated identifiers, followed by the title:

Example 1, case ECLI:NL:RBZLY:2012:BW8752:
> De beslissing berust op de **artikelen 10, 14a, 14b, 14c, 14d, 22c, 22d, 36f, 48, 300 en 304 van het Wetboek van Strafrecht**, zoals de artikelen luidden ten tijde van het bewezen verklaarde. ()
These should be identified as 11 seperate links to _Wetboek van Strafrecht_.

Example 2, 

**2. Lid**

Example 1, case ECLI:NL:HR:2022:380:
> Besluit van 22 januari 2021, Stb. 2021, 24, houdende inwerkingtreding en inwerkingstelling van **artikel 8, eerste en derde lid, van de Wet buitengewone bevoegdheden burgerlijk gezag**.

