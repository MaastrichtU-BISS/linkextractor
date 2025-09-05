from src import search

# "Artikel 7.28 WHW",
# "Artikel 7.57H WHW"

def test_simple():
    results = search.query_exact("Artikel 7.28 WHW")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['type'] == 'artikel', "should be type artikel"
    assert result['bwb_id'] == 'BWBR0005682', "should be identifier for BW book 5"
    assert result['number'] == '7.28', "should be article number 7.28"
    assert 'book' not in result['fragment'] or result['fragment']['book'] == None, "should not have a book number"

def test_simple_suffix():
    results = search.query_exact("Artikel 7.57H WHW")

    assert len(results) == 1, "should be one result"
    result = results[0]

    print(result)

    assert result['type'] == 'artikel', "should be type artikel"
    assert result['bwb_id'] == 'BWBR0005682', "should be identifier for BW book 5"
    assert result['number'] == '7.57H', "should be article number 7.57H"
    assert 'book' not in result['fragment'] or result['fragment']['book'] == None, "should not have a book number"
