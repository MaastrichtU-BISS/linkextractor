from linkextractor import search

# "Artikel 7.28 WHW",
# "Artikel 7.57H WHW"

def test_simple():
    results = search.extract_links("Artikel 7.28 WHW", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005682', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '7.28', "should be article number 7.28"
    assert 'boek' not in result['fragment'] or result['fragment']['boek'] == None, "should not have a boek fragment"

def test_simple_suffix():
    results = search.extract_links("Artikel 7.57H WHW", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005682', "should be identifier for BW book 5"
    assert result['fragment']['artikel'] == '7.57H', "should be article number 7.57H"
    assert 'boek' not in result['fragment'] or result['fragment']['boek'] == None, "should not have a boek fragment"
