# Analyze opportunities for improvement of reference extraction recall (WIP / Parked)

The purpose of this subproject of linkextractor-lite is to go through all caselaw texts and attempt to extract references using the linkextractor-lite logic. The extracted links will be compared to the links in the database, originating from LIDO. First, mostly manual analysis will be done to check whether we're extracting references that were not considered by LIDO, or whether LIDO has references that we are not considering.

## Method 1: Replicate linkextraction to find differences

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

## Results 1

In this paragraph, misclassifications will be indentified.

### False Positives

These links are links we recognized but are not recognized by lido. Either because:
- we incorrectly indentified them as links or identified them as the wrong link, or
- we correctly identified them as a link, while lido missed it (here the real gains can be achieved)

**1. Ambiguous aliases**

Rv

**2. Unique opschrifts** (partially solved ✅)

It seems that the links of lido are unique by opschrifts. Meaning, if there are multiple occurances of the same opschrift, they will be noted as (an amount) of 1. 
To equalize the results between lido and custom, we therefore have to ensure that custom also groups by opschrift (`context->literal`) to ensure we don't falsely flag these as FP.
Do note that custom also takes into account the spans, and for the analysis ensures that each span is only considered as a unique result.

Example 1, case `ECLI:NL:HR:2022:380`:
Here "art. 3 Wbbbg" occurs three times in the full-text. However, it is only listed once in the links of lido. 
In custom, these are caught as three individual links, distinguished by the unique span.

**Solution**:
Deduplicate the custom links before passing to the comparison function, to ensure same results.

One remaining issue, is the case for conjoined links in one reference, such as "artikel 3:105 en 3:306 BW".
In this case, there are two links with an identical reference string, refering to different laws. In this case, they should be treated as seperate and not be joined.
This issue will be solved after the issue of conjunction is solved.

**3. Substring matches**

Example 1, case `ECLI:NL:HR:2022:380`:
In the following string
> Art. 1 lid 1 Wbbbg
the substring
> **Art. 1 li**
is interpreted as article 1 of _"Leidraad invordering"_ of which the alias is Li

### False Negatives

These are links that the custom link-extractor did not recognize.

**1. Conjunctions**

In some cases, there are multiple references conjoined in a single match/string. For example, having the literal "artiekelen" followed by a list of comma-seperated identifiers, followed by the title:

Example 1, case `ECLI:NL:RBZLY:2012:BW8752`:
> De beslissing berust op de **artikelen 10, 14a, 14b, 14c, 14d, 22c, 22d, 36f, 48, 300 en 304 van het Wetboek van Strafrecht**, zoals de artikelen luidden ten tijde van het bewezen verklaarde.
These should be identified as 11 seperate links to _Wetboek van Strafrecht_.


Example 2, case `ECLI:NL:GHSHE:2018:3030`:
> (...) aan alle uit **artikel 3:105 jo. 3:306 BW** voortvloeiende vereisten 

**Proposal**
We could extend the current regex patterns to capture the repeated article identifiers followed by conjunction literals. 
Ideally, it would detect that there are repeated instances of the identifiers and create a list of the capture group.
In reality, it is probably more feasible to extend the pattern to capture the string, but then manually check afterwards if the captured identifier (possibly containing multiple identifiers) can be split-up by conjunction literals.

**2. Lid or conjunction**

There's various ways to write a lid.

Example 1, case `ECLI:NL:HR:2022:380`:
> Besluit van 22 januari 2021, Stb. 2021, 24, houdende inwerkingtreding en inwerkingstelling van **artikel 8, eerste en derde lid, van de Wet buitengewone bevoegdheden burgerlijk gezag**.

This one is rather difficult to capture, because:
1. "eerste en derde lid" is difficult to interpret consitently
2. the comma's can be interpreted as a conjunction of articles

Another case is:
Example 2, case X:
> artikel 7:10, leden 1 en 3, van de Awb

where the conjunction is between subparagraphs.


## Manual discoveries

For some cases, neither lido nor this repo correctly parsed specific references. These parsing errors will be layed out here.

**Inbox**
This is a list of references I found manually that were not appropriately discovered by lido 
- case `ECLI:NL:GHARL:2025:5628`:
    - > artikel 1.2 aanhef en onder c van het Landelijk Procesreglement voor civiele dagvaardingszaken bij de gerechtshoven (LPR)
    - > artikel 1b onder 1 Wte (oud).
        - references "Wet toezicht effectenverkeer 1995" https://wetten.overheid.nl/BWBR0007657/2022-10-01#HoofdstukI_Artikel1
        - interestingly, only article 1 is identified, while all elements are a list
        - onder 1 refers to the first item under item 'a' in the list
        - this could be manualy mapped to article 1, as it's technically correct at its granular level
    - apparently, this is consistently being misidentified across cases, see:
        - `ECLI:NL:GHARL:2025:5631` among others
- case `ECLI:NL:HR:2008:BD1494`:
    - > (...) toestemming als bedoeld in artikel 6 BWA 1945.
        - should be caught by this repo
- case X:
    - > In gevolge artikel 1:253q, vijfde lid van het BW "juncto 1:253r, eerste lid van het BW"
        - the second part, from "juncto", is not captured, since the conjunction happens after the resource title (BW) without an identifier for an article (art.)
case `ECLI:NL:RBROT:2024:3831`:
    - > "artikel 3.9, derde lid, eerste zin, van de Wabo"
        - alleen Wabo is herkend
    - > "artikel 4.3, aanhef en onder a, van de Invoeringswet Omgevingswet" -> in bijlage?
    - > "artikel 2:12, tweede lid, van de APV" -> refereert naar lokale wetgeving (https://lokaleregelgeving.overheid.nl/CVDR647979/2)
    - > "artikel 1.29 van de planregels"
    - > "artikel 6.2.1 van de planregels"
    - > "artikel 2.1, eerste lid, onder a, de omgevingsvergunning"


**1. Ommitted `art` prefix for an article**

Example 1, case `ECLI:NL:RBNHO:2025:9145`:
> (...) is van strijd met artikel 5:52 BW of onrechtmatige hinder als bedoeld in **5:37 BW**, zal de rechtbank (...)

In here, there reference to "*5:37 BW*" was not caught by lido as an article, but only the law reference "BW".

**2. Dots in article**

Example 1, case `ECLI:NL:GHARL:2025:5628`:
> artikel 1.2 aanhef en onder c van het Landelijk Procesreglement voor civiele dagvaardingszaken bij de gerechtshoven (LPR) 

**3. Incorrect parsing on linkeddata on page of "document with links**

As mentioned before, LIDO joins all extracted references by their _opschrift_, case insensitively.
On the linkeddata.overheid.nl document-with-links viewer for cases, it can be seen that a reference that was correctly identified by them, is incorrectly replaced as a hyperlink, 
probably due to them trying to replace the lowercase values in the text with links.

This was discovered when researching if lido has metadata about multiple _opschrifts_, this output verifying the opposite. (See: ECLI:NL:GHSHE:2018:3030, "Artikel 5:50 BW")

## Method 2: Quickly discover FN from LIDO

Alterantively to above approach, we could fast forward to discovering FNs from LIDO (as in, parts of full-texts that LIDO should have recognized as a link, but didn't) 
by scanning full-texts for specific indicators/tokens that indicate a probable reference. Then, these parts can be checked autoamatically against the 
DB to verify that the LIDO caught this as a link. If it didn't, we'll log it to a file, after which manual inspection should clarify if it is actually a FN or a FFN.

After inspection, a mapping can be constructed to map from string literals in full-texts to articles. After multiple iterations, the consistency should increase.

### Link indicators

**1. Article indicator**
If (variations of) the word "article" are present in the text, this usually indicates a link to a law. If this piece is not part of a reference in the DB of LIDO, this might be 
a mistake.

Example (regex) patterns:
- `art.?\s+` # short spelling
- `artikel` # full spelling
- `article` # english
- `artiekel` # misspelling

**2. Lid indicator**
Many references to articles contain specific seperators and numbers, such as:
- `(?:lid|leden)\s+[0-9a-z]`
 
**3. Article seperator**
Many references to articles contain specific seperators and numbers, such as:
- `[0-9]+[:.][0-9a-z]+`
