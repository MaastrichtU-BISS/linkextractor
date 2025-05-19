echo "enter commands inside this script manually"
return

# Pipeline for cases

time cat lido-export.ttl \
| serdi -l -i turtle -o ntriples - \
| grep "^<http://linkeddata.overheid.nl/terms/jurisprudentie/id/" \
| fgrep \
    -e "<http://purl.org/dc/terms/identifier>" \
    -e "<http://purl.org/dc/terms/type>" \
    -e "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>" \
    -e "<http://purl.org/dc/terms/title>" \
    -e "<http://www.w3.org/2004/02/skos/core#prefLabel>" \
    -e "<http://www.w3.org/2000/01/rdf-schema#label>" \
    -e "<http://linkeddata.overheid.nl/terms/refereertAan>" \
    -e "<http://linkeddata.overheid.nl/terms/linkt>" \
    -e "<http://linkeddata.overheid.nl/terms/heeftZaaknummer>" \
    -e "<http://linkeddata.overheid.nl/terms/heeftUitspraakdatum>" \
> lido-cases.nt
real    10m38,268s

time sort -k1,1 lido-cases.nt > lido-cases-sort.nt
real    6m53,953s

cat lido-cases-sort.nt | fgrep "http://purl.org/dc/terms/type" | wc -l
3619971

# Pipeline for cases

time cat lido-export.ttl \
| serdi -l -i turtle -o ntriples - \
| grep "^<http://linkeddata.overheid.nl/terms/bwb/id/" \
| fgrep \
    -e "<http://purl.org/dc/terms/identifier>" \
    -e "<http://purl.org/dc/terms/type>" \
    -e "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>" \
    -e "<http://linkeddata.overheid.nl/terms/isOnderdeelVan>" \
    -e "<http://linkeddata.overheid.nl/terms/isOnderdeelVanRegeling>" \
    -e "<http://purl.org/dc/terms/title>" \
    -e "<http://www.w3.org/2004/02/skos/core#prefLabel>" \
    -e "<http://www.w3.org/2000/01/rdf-schema#label>" \
    -e "<http://linkeddata.overheid.nl/terms/heeftJuriconnect>" \
    -e "<http://linkeddata.overheid.nl/terms/heeftOnderdeelNummer>" \
> lido-law.nt
real    10m42,122s

error n: 983

time sort -k1,1 lido-law.nt > lido-law-sort.nt
real    7m35,347s

cat lido-law-sort.nt | fgrep "http://purl.org/dc/terms/type" | wc -l
1026893