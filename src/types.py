from typing import List, NotRequired, TypedDict

class Resource(TypedDict):
    name: str
    bwb_id: str
    bwb_label_id: NotRequired[str]


class Fragment(TypedDict):
    book: NotRequired[str]
    article: NotRequired[str]


class Link(TypedDict):
    resource: Resource
    fragment: NotRequired[Fragment]

LinkList = List[Link]