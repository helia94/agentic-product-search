from dataclasses import dataclass
import re
from typing import Iterable, Optional, List
from typing_extensions import Annotated, TypedDict
import json

@dataclass
class Document:
    id: str
    title: str
    url: str
    content: str

class SourcedFact(TypedDict):
    fact: str
    document_id: str

class SourcedFactsList(TypedDict):
    facts: List[SourcedFact]


class DocumentStore(list[Document]):
    def __init__(self, docs: Optional[Iterable[Document]] = None):
        super().__init__(docs or [])

    @staticmethod
    def _slug(title: str) -> str:
        return re.sub(r'[^\w\s-]', '', title.lower()).replace(" ", "_").strip() or "doc"

    def _ensure_unique_id(self, doc: Document) -> Document:
        if not doc.id:
            doc.id = self._slug(doc.title)
        # ensure uniqueness inside this list
        ids = {d.id for d in self}
        if doc.id in ids:
            base = doc.id
            k = 1
            while f"{base}_{k}" in ids:
                k += 1
            doc.id = f"{base}_{k}"
        return doc

    def append(self, doc: Document) -> None:
        super().append(self._ensure_unique_id(doc))

    def extend(self, docs: Iterable[Document]) -> None:
        for d in docs:
            self.append(d)

    def __add__(self, other):
        out = DocumentStore(self)
        if isinstance(other, Document):
            out.append(other)
        else:
            out.extend(list(other))
        return out

    def __iadd__(self, other):
        if isinstance(other, Document):
            self.append(other)
        else:
            self.extend(list(other))
        return self

    @staticmethod
    def add_documents_from_tavily(tavily_docs: dict) -> None:
        documents = DocumentStore([
            Document(
                id=DocumentStore._slug(doc.get("title","")),
                title=doc.get("title",""),
                url=doc.get("url",""),
                content=doc.get("content","")
            )
            for doc in tavily_docs["results"]
        ])
        if "answer" in tavily_docs:
            documents.append(Document(
                id="answer",
                title="Answer",
                url="",
                content=tavily_docs["answer"]
            ))
        return documents

    def recreate_from_sourced_facts(self, facts: list[SourcedFact]):
        """Recreate documents from sourced facts, preserving IDs"""
        load_as_dic = json.loads(facts) if isinstance(facts, str) else facts
        load_as_dic = load_as_dic["facts"]
        new_docs = []
        for fact in load_as_dic:
            old_doc = self.get_document_by_id(fact["document_id"])
            if old_doc:
                new_docs.append(Document(
                    id=old_doc.id,
                    title=old_doc.title,
                    url=old_doc.url,
                    content=fact["fact"]
                ))
            else:
                new_docs.append(Document(
                    id="Unknown",
                    title="Unknown",
                    url="Unknown",
                    content=fact["fact"]
                ))
            
        return DocumentStore(new_docs)
    
    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        for doc in self:
            if doc.id == doc_id:
                return doc
        return None

    def get_document_content_as_str(self) -> str:
        return "\n\n".join(
            f"[content: {d.content}, ref:{d.id}]"
            for d in self
        ) or "No documents found."

    def keep_relevant_documents(self, relevant_ids: list[str]) -> None:
        # filter in place, preserve order
        new_list = [d for d in self if d.id in relevant_ids]
        self.clear()
        self.extend(new_list)
        return self
    
    @staticmethod
    def merge(stores: List['DocumentStore']) -> 'DocumentStore':
        merged_store = DocumentStore()
        for store in stores:
            merged_store += store
        return merged_store

def reduce_documents(left: DocumentStore, right: Iterable[Document] | Document | None):
    out = DocumentStore(left)
    if right is None:
        return out
    if isinstance(right, Document):
        out.append(right)
    else:
        out.extend(right)
    return out