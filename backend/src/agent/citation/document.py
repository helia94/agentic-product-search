from dataclasses import dataclass
import re


@dataclass
class Document:
    """A document to be cited in a response."""
    id: str
    title: str
    url: str
    content: str


class DocumentStore:
    def __init__(self):
        self.documents = {}

    def add_document(self, doc: Document):
        # Ensure the document ID is unique; append an integer if needed
        base_id = doc.id
        counter = 1
        while doc.id in self.documents:
            doc.id = f"{base_id}_{counter}"
            counter += 1
        self.documents[doc.id] = doc

    def add_documents(self, docs: list[Document]):
        for doc in docs:
            self.add_document(doc)

    def get_document_content_as_str(self) -> str:
        return "\n\n".join(
            f"[content: {doc.content}, ref:{doc.id}]"
            for doc in self.documents.values()
        ) or "No documents found."

    def keep_relevant_documents(self, relevant_ids: list[str]):
        self.documents = {
            doc_id: doc
            for doc_id, doc in self.documents.items()
            if doc_id in relevant_ids
        }

    def add_documents_from_tavily(
        self,
        tavilyt_docs: list[dict],
    ):
        docs = [
            Document(
                id=self._make_id(doc.get("title", "")),
                title=doc.get("title", ""),
                url=doc.get("url", ""),
                content=doc.get("content", ""),
            )
            for doc in tavilyt_docs
        ]
        self.add_documents(docs)

    def _make_id(self, title: str) -> str:
        return re.sub(r'[^\w\s-]', '', title.lower()).replace(" ", "_").strip()