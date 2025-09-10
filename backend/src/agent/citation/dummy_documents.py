from agent.citation.document import DocumentStore, Document

DUMMY_DOC_1 = Document("id_1", "Fact 1", "http://example.com/doc1", "This is the content of document 1.")
DUMMY_DOC_2 = Document("id_2", "Fact 2", "http://example.com/doc2", "This is the content of document 2.")

DUMMY_DOCUMENTS = DocumentStore([DUMMY_DOC_1, DUMMY_DOC_2
])