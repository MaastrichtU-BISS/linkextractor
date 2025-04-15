from src import search

# "5:1 BW",
# "Art. 5:1 BW",
# "Art. 5:1 lid 2 BW",

def test_no_art():
    results = search.query_exact("5:1 BW")
    
    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['article'] == '1', "should be article number 1"
    assert result['fragment']['book'] == '5', "should be book number 5"

def test_art_simple():
    results = search.query_exact("Art. 5:1 BW")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['article'] == '1', "should be article number 1"
    assert result['fragment']['book'] == '5', "should be book number 5"

def test_art_expressive():
    results = search.query_exact("Artikel 1 van boek 5 van het Burgerlijk Wetboek")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['article'] == '1', "should be article number 1"
    assert result['fragment']['book'] == '5', "should be book number 5"

def test_art_expressive_2():
    results = search.query_exact("Burgerlijk Wetboek Boek 5, Artikel 1")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['article'] == '1', "should be article number 1"
    assert result['fragment']['book'] == '5', "should be book number 5"

def test_art_expressive_lid():
    results = search.query_exact("Artikel 1 lid 2 van boek 5 van het Burgerlijk Wetboek")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['article'] == '1', "should be article number 1"
    assert result['fragment']['book'] == '5', "should be book number 5"
    assert result['fragment']['subparagraph'] == '2', "should be subparagraph 2"

def test_art_lid():
    results = search.query_exact("Art. 5:1 lid 2 BW")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005288', "should be identifier for BW book 5"
    assert result['fragment']['article'] == '1', "should be article 1"
    assert result['fragment']['book'] == '5', "should be book 5"
    assert result['fragment']['subparagraph'] == '2', "should be subparagraph 2"
