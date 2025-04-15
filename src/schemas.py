from typing import TypedDict

class ResourceIdentifiers(TypedDict):
  bwbId: str
  ecliId: str

class Resource(TypedDict):
  id: str
  # type: str
  title: str
  identifiers: ResourceIdentifiers

class BookInfo(TypedDict, total=False):
    number: int
    title: str


class TitleInfo(TypedDict, total=False):
    number: int
    title: str


class ChapterInfo(TypedDict, total=False):
    number: int
    title: str


class SectionInfo(TypedDict, total=False):
    number: str
    title: str
    type: str


class ArticleInfo(TypedDict, total=False):
    number: str
    title: str


class ParagraphInfo(TypedDict, total=False):
    number: int
    type: str  # "lid" in Dutch, "paragraph" in English


class SubParagraphInfo(TypedDict, total=False):
    letter: str
    number: int


class RangeInfo(TypedDict, total=False):
    articles: str
    paragraphs: str


class FragmentCustomInfo(TypedDict, total=False):
    deel: str
    onderdeel: str


class Fragment(TypedDict, total=False):
    book: BookInfo                 # boek
    titlepart: TitleInfo               # titel(deel)
    chapter: ChapterInfo           # hoofdstuk
    section: SectionInfo           # afdeling
    article: ArticleInfo           # artikel
    paragraph: ParagraphInfo       # paragraaf
    subParagraph: SubParagraphInfo # lid
    ranges: RangeInfo

class Reference(TypedDict):
  resource: Resource
  fragmnet: Fragment
  