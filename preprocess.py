import os
import re
# import lxml.etree as ET
from saxonche import PySaxonProcessor
import requests
import zipfile
import typing
import json

FILE_BWB_STYLESHEET = "./data/static/xsl/bwb-regeling-aanduiding.xslt"
FILE_BWB_IDS_TRANSFORMED = "./data/dynamic/bwb/BWBIdList.server.xml"
FILE_BWB_IDS_XML = "./data/dynamic/bwb/BWBIdList.xml"
FILE_BWB_IDS_JSON = "./data/dynamic/bwb/BWBIdList.json"
FILE_BWB_IDS_ZIP = f"{FILE_BWB_IDS_XML}.zip"
URL_BWB_IDS_ZIP = "https://zoekservice.overheid.nl/BWBIdService/BWBIdList.xml.zip"

def prepare_bwb_trie(when_exists: typing.Literal["error", "overwrite", "continue"] = "error"):

  def download_bwb_id_xml():
    print("- - Downloading BWB id xml")
    if os.path.exists(URL_BWB_IDS_ZIP):
      if when_exists == "error":
        raise Exception(f"File {URL_BWB_IDS_ZIP} already exists")
      elif when_exists == "continue":
        return
      elif when_exists == "overwrite":
        pass
    
    response = requests.get(URL_BWB_IDS_ZIP)
    with open(FILE_BWB_IDS_ZIP, "wb") as file:
        file.write(response.content)
    
    if not os.path.exists(FILE_BWB_IDS_ZIP):
      raise Exception(f"Failed downloading file {FILE_BWB_IDS_ZIP}")
    print(f"- - File downloaded to {FILE_BWB_IDS_ZIP}")


  def extract_bwb_id_xml():
    print("- - Extracting BWB ID list")
    if os.path.exists(FILE_BWB_IDS_XML):
      if when_exists == "error":
        raise Exception(f"File {FILE_BWB_IDS_XML} already exists")
      elif when_exists == "continue":
        return
      elif when_exists == "overwrite":
        pass
    
    if not os.path.exists(FILE_BWB_IDS_ZIP):
      raise Exception(f"File to extract {FILE_BWB_IDS_ZIP} not found")
    
    with zipfile.ZipFile(FILE_BWB_IDS_ZIP, 'r') as zip_ref:
        zip_ref.extract("BWBIdList.xml", os.path.dirname(FILE_BWB_IDS_XML))
    if not os.path.exists(FILE_BWB_IDS_XML):
      raise Exception("Failed extracting file")
    
  def parse_bwb_xslt():
    print("- - Parsing XML BWB ID list")
    if os.path.exists(FILE_BWB_IDS_TRANSFORMED):
      if when_exists == "error":
        raise Exception(f"Failed creating parsed file {FILE_BWB_IDS_TRANSFORMED}")
      elif when_exists == "continue":
        return
      elif when_exists == "overwrite":
        pass

    if not os.path.exists(FILE_BWB_IDS_XML):
      raise Exception(f"File to parse {FILE_BWB_IDS_XML} not found")
    if not os.path.exists(FILE_BWB_STYLESHEET):
      raise Exception(f"File parse-specification {FILE_BWB_STYLESHEET} not found")
    
    with PySaxonProcessor(license=False) as proc:
      xslt_proc = proc.new_xslt30_processor()
      xslt_proc.transform_to_file(source_file=FILE_BWB_IDS_XML, 
                                  stylesheet_file=FILE_BWB_STYLESHEET,
                                  output_file=FILE_BWB_IDS_TRANSFORMED)
    
    if not os.path.exists(FILE_BWB_IDS_TRANSFORMED):
      raise Exception(f"Failed creating parsed file {FILE_BWB_IDS_TRANSFORMED}")
  

  def parse_bwb_manual():
    print("- Parsing tree")

    """
    TestCase:
    <item id="BWBR0002534">
      <title>Wet van 21 juli 1966, houdende vervanging van de Motorrijtuigenbelastingwet (Stb. 1926, 464) door een nieuwe wettelijke regeling</title>
      <title>Wet op de motorrijtuigenbelasting 1966</title>
      <title>MRB</title>
      <title>Wet MRB 1966</title>
    </item>
    """

    from lxml import etree

    output = []

    NS = {"NS1": "http://schemas.overheid.nl/bwbidservice"}

    root = etree.parse(FILE_BWB_IDS_XML)
    regelingLijst = root.find('NS1:RegelingInfoLijst', namespaces=NS)
    for regeling in regelingLijst.iterfind('NS1:RegelingInfo', namespaces=NS):
      bwbId = regeling.find('NS1:BWBId', namespaces=NS).text
      titelOfficieel = regeling.find('NS1:OfficieleTitel', namespaces=NS).text
      citeerTitels = [
        titel.find('NS1:titel', namespaces=NS).text 
        for titel 
        in regeling
          .find('NS1:CiteertitelLijst', namespaces=NS)
          .iterfind('NS1:Citeertitel', namespaces=NS)
      ]
      afkortingen = [
        afkorting.text 
        for afkorting
        in regeling
          .find('NS1:AfkortingLijst', namespaces=NS)
          .iterfind('NS1:Afkorting', namespaces=NS)
      ]
      titelsNietOfficieel = [
        titel.text 
        for titel 
        in regeling
          .find('NS1:NietOfficieleTitelLijst', namespaces=NS)
          .iterfind('NS1:NietOfficieleTitel', namespaces=NS)
      ]

      titels = [titelOfficieel] + citeerTitels + afkortingen + titelsNietOfficieel

      # limit length and remove some unwanted chars
      titels = [
        re.sub(r'\s+', ' ', 
          re.sub(r'^(\s|[.,;:])+', '', titel)
        )
        for titel in titels
        if titel and len(titel) > 0 and len(titel) < 2500
      ]

      output.append([bwbId, titels])
    
    with open(FILE_BWB_IDS_JSON, "w", encoding="utf-8") as f:
      json.dump(output, f, ensure_ascii=False, indent=2)
    

  # download_bwb_id_xml()
  # extract_bwb_id_xml()
  parse_bwb_manual()
  # parse_bwb_xslt()

if __name__ == "__main__":
  print("Starting preprocessing")
  # prepare_bwb_trie("overwrite")
  prepare_bwb_trie("continue")