import re

RE_BWB_FROM_LIDO_ID = re.compile(r"\/terms\/bwb\/id\/(.*?)\/")
RE_ECLI_FROM_LIDO_ID = re.compile(r"\/terms\/jurisprudentie\/id\/(.*?)$")

TERM_URI_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'

REGELING_ONDERDELEN = {
    'http://linkeddata.overheid.nl/terms/Wet': 'wet',
    'http://linkeddata.overheid.nl/terms/Deel': 'deel',
    'http://linkeddata.overheid.nl/terms/Boek': 'boek',
    'http://linkeddata.overheid.nl/terms/Titeldeel': 'titeldeel',
    'http://linkeddata.overheid.nl/terms/Hoofdstuk': 'hoofdstuk',
    'http://linkeddata.overheid.nl/terms/Artikel': 'artikel',
    'http://linkeddata.overheid.nl/terms/Paragraaf': 'paragraaf',
    'http://linkeddata.overheid.nl/terms/SubParagraaf': 'subparagraaf',
    'http://linkeddata.overheid.nl/terms/Afdeling': 'afdeling',
}
