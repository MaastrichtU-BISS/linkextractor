from src import search


# "Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)",
# "Artikel 4:8 AWB",
# "Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel)",
# "4:8 Awb",

def test_awb_48():
    results = search.query_exact("Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005537', "should be identifier for AWB"
    assert result['fragment']['article'] == '4:8', "should be article number 4:8"
    assert 'book' not in result['fragment'] or result['fragment']['book'] == None, "should not have a book number"

def test_awb_48():
    results = search.query_exact("Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel)")

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['id'] == 'BWBR0005537', "should be identifier for AWB"
    assert result['fragment']['article'] == '3:2', "should be article number 3:2"
    assert 'book' not in result['fragment'] or result['fragment']['book'] == None, "should not have a book number"