from src import search

# "5:1 BW",
# "Art. 5:1 BW",
# "Art. 5:1 lid 2 BW",

def test_no_art():
    results = search.extract_links("5:1 BW", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '1', "should be article number 1"
    assert result['fragment']['boek'] == '5', "should be book number 5"

def test_art_simple():
    results = search.extract_links("Art. 5:1 BW", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '1', "should be article number 1"
    assert result['fragment']['boek'] == '5', "should be book number 5"

def test_art_expressive():
    results = search.extract_links("Artikel 1 van boek 5 van het Burgerlijk Wetboek", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '1', "should be article number 1"
    assert result['fragment']['boek'] == '5', "should be book number 5"

def test_art_expressive_2():
    results = search.extract_links("Burgerlijk Wetboek Boek 5, Artikel 1", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '1', "should be article number 1"
    assert result['fragment']['boek'] == '5', "should be book number 5"

def test_art_expressive_lid():
    results = search.extract_links("Artikel 1 lid 2 van boek 5 van het Burgerlijk Wetboek", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '1', "should be article number 1"
    assert result['fragment']['boek'] == '5', "should be book number 5"
    assert result['fragment']['subparagraaf'] == '2', "should be subparagraph 2"

def test_art_lid():
    results = search.extract_links("Art. 5:1 lid 2 BW", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '1', "should be article 1"
    assert result['fragment']['boek'] == '5', "should be book 5"
    assert result['fragment']['subparagraaf'] == '2', "should be subparagraph 2"
