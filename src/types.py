from typing import List, NotRequired, TypedDict

class Resource(TypedDict):
    title: str
    bwb_id: str
    bwb_label_id: NotRequired[str]


class Fragment(TypedDict):
    boek: NotRequired[str]
    artikel: NotRequired[str]


class Link(TypedDict):
    resource: Resource
    fragment: NotRequired[Fragment]

LinkList = List[Link]

class Alias(TypedDict):
    bwb_id: str
    alias: str

AliasList = List[Alias]