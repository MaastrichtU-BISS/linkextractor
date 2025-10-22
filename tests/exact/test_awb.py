import logging
from src import search


# "Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)",
# "Artikel 4:8 AWB",
# "Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel)",
# "4:8 Awb",

def test_awb_48():
    logging.basicConfig(level=logging.DEBUG)

    results = search.extract_links("Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    print(result)

    assert result['resource']['bwb_id'] == 'BWBR0005537', "should be identifier for AWB"
    assert result['fragment']['artikel'] == '4:8', "should be article number 4:8"
    assert 'boek' not in result['fragment'] or result['fragment']['boek'] == None, "should not have a boek fragment"

def test_awb_32():
    results = search.extract_links("Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel)", exact=True)

    assert len(results) == 1, "should be one result"
    result = results[0]

    assert result['resource']['bwb_id'] == 'BWBR0005537', "should be identifier for AWB"
    assert result['fragment']['artikel'] == '3:2', "should be article number 3:2"
    assert 'boek' not in result['fragment'] or result['fragment']['boek'] == None, "should not have a boek fragment"
