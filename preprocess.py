import os
import lxml.etree as ET
import requests
import zipfile

FILE_XSLT_BWB_REGELING = "./data/static/xsl/bwb-regeling-aanduiding.xslt"
FILE_XML_BWB_ID_LIST = "./data/dynamic/bwb/BWBIdList.xml"
FILE_BWB_RESULT = "./data/dynamic/bwb/RESULT"
FILE_XML_BWB_ID_LIST_ZIP = f"{FILE_XML_BWB_ID_LIST}.zip"
# URL_XML_BWB_ID_LIST = "https://zoekservice.overheid.nl/BWBIdService/BWBIdList.xml.zip!/BWBIdList.xml" # <-- for some reason they used this format, but below seems to have same effect
URL_XML_BWB_ID_LIST_ZIP = "https://zoekservice.overheid.nl/BWBIdService/BWBIdList.xml.zip"

def prepare_bwb_trie():
  print("- Preparing BWB trie")

  def download_bwb_id_xml():
    print("- - Downloading BWB id xml")
    if os.path.exists(URL_XML_BWB_ID_LIST_ZIP):
      raise Exception(f"File {URL_XML_BWB_ID_LIST_ZIP} already exists")
    
    response = requests.get(URL_XML_BWB_ID_LIST_ZIP)
    with open(FILE_XML_BWB_ID_LIST_ZIP, "wb") as file:
        file.write(response.content)
    
    if not os.path.exists(FILE_XML_BWB_ID_LIST_ZIP):
      raise Exception(f"Failed downloading file {FILE_XML_BWB_ID_LIST_ZIP}")
    print(f"- - File downloaded to {FILE_XML_BWB_ID_LIST_ZIP}")


  def extract_bwb_id_xml():
    print("- - Extracting BWB ID list")
    if not os.path.exists(FILE_XML_BWB_ID_LIST_ZIP):
      raise Exception(f"File to extract {FILE_XML_BWB_ID_LIST_ZIP} not found")
    if os.path.exists(FILE_XML_BWB_ID_LIST):
      raise Exception(f"File {FILE_XML_BWB_ID_LIST} already exists")
    
    with zipfile.ZipFile(FILE_XML_BWB_ID_LIST_ZIP, 'r') as zip_ref:
        zip_ref.extract("BWBIdList.xml", os.path.dirname(FILE_XML_BWB_ID_LIST))
    if not os.path.exists(FILE_XML_BWB_ID_LIST):
      raise Exception("Failed extracting file")
    
  def parse_bwb_xslt():
    print("- - Parsing XML BWB ID list")
    if not os.path.exists(FILE_XML_BWB_ID_LIST):
      raise Exception(f"File to parse {FILE_XML_BWB_ID_LIST} not found")
    if not os.path.exists(FILE_XSLT_BWB_REGELING):
      raise Exception(f"File parse-specification {FILE_XSLT_BWB_REGELING} not found")

    dom = ET.parse(FILE_XML_BWB_ID_LIST)
    xslt = ET.parse(FILE_XSLT_BWB_REGELING)
    transform = ET.XSLT(xslt)
    result = transform(dom)
    with open(FILE_BWB_RESULT) as f:
      f.write(ET.tostring(result, pretty_print=True))
    
    if not os.path.exists(FILE_BWB_RESULT):
      raise Exception(f"Failed creating parsed file {FILE_BWB_RESULT}")


  
  download_bwb_id_xml()
  extract_bwb_id_xml()
  parse_bwb_xslt()

if __name__ == "__main__":
  print("Starting preprocessing")
  prepare_bwb_trie()