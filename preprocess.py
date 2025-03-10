import os
# import lxml.etree as ET
from saxonche import PySaxonProcessor
import requests
import zipfile
import typing

FILE_BWB_STYLESHEET = "./data/static/xsl/bwb-regeling-aanduiding.xslt"
FILE_BWB_IDS_TRANSFORMED = "./data/dynamic/bwb/BWBIdList.server.xml"
FILE_BWB_IDS_XML = "./data/dynamic/bwb/BWBIdList.xml"
FILE_BWB_IDS_ZIP = f"{FILE_BWB_IDS_XML}.zip"
# URL_XML_BWB_ID_LIST = "https://zoekservice.overheid.nl/BWBIdService/BWBIdList.xml.zip!/BWBIdList.xml" # <-- for some reason they used this format, but below seems to have same effect
URL_BWB_IDS_ZIP = "https://zoekservice.overheid.nl/BWBIdService/BWBIdList.xml.zip"

def prepare_bwb_trie(when_exists: typing.Literal["error", "overwrite", "continue"] = "error"):
  print("- Preparing BWB trie")

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
  
  download_bwb_id_xml()
  extract_bwb_id_xml()
  parse_bwb_xslt()

# test_cont = """<document><lx:regeling>xyz</lx:regeling></document>"""
# test_cont = """<lx:text><lx:regeling>xyz</lx:regeling></lx:text>"""
# test_cont = """<lx:regeling lokale_alias="BW">Burgerlijk Wetboek</lx:regeling>, artikel 5, lid 2."""
test_cont = """artikel 5, lid 2."""

def build_db():
  pass


def prepare_wayeye():
  # https://github.com/waxeye-org/waxeye/blob/master/docs/book/book#L812
  import waxeye
  import parser_le_links
  import parser_le_eu_regelgeving

  # $ /opt/lx/waxeye/bin/waxeye -g python . -m grammars/le-links.waxeye
  p = parser_le_eu_regelgeving.Parser()
  # ast = p.parse("Artikel 6:162 BW")
  # ast = p.parse("""<lx:regeling>Wist je dat artikel 10:56 van het Burgerlijk Wetboek en artikel 56 van het Burgerlijk Wetboek Boek 10 hetzelfde zijn?</lx:regeling>""")

  ast = p.parse(test_cont)

  print("OUTPUT:")
  print(ast)

  pass


if __name__ == "__main__":
  print("Starting preprocessing")
  prepare_bwb_trie("overwrite")
  # prepare_bwb_trie("continue")
  # prepare_wayeye()