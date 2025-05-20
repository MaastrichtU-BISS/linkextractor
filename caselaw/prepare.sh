echo "enter commands inside this script manually"
return

# setup
# 1. download serdi from https://launchpad.net/ubuntu/plucky/amd64/serdi/0.32.4-1
wget http://launchpadlibrarian.net/775571639/serdi_0.32.4-1_amd64.deb
sudo dpkg -i serdi_0.32.4-1_amd64.deb

# 2. download turtle export
wget https://linkeddata.overheid.nl/export/lido-export.ttl.gz

# Pipeline for cases

time zcat lido-export.ttl.gz \
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

time zcat lido-export.ttl.gz \
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