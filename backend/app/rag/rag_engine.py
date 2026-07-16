"""
AURA RAG (Retrieval-Augmented Generation) Engine
--------------------------------------------------
Handles:
  1. Document ingestion  — PDF/text → chunks → embeddings → ChromaDB
  2. Retrieval           — semantic search over stored chunks
  3. RAG response        — inject retrieved context into LLM prompt

Pipeline:
  Upload file
      ↓
  Load with pypdf / plain text reader
      ↓
  Split into chunks (RecursiveCharacterTextSplitter)
      ↓
  Embed with HuggingFace sentence-transformers (bge-small-en-v1.5)
      ↓
  Store in ChromaDB (persisted to disk)
      ↓
  On query → similarity search → top-k chunks → LLM with context
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama

from app.database.config import settings

logger = logging.getLogger(__name__)

# ── Embedding Model (singleton) ────────────────────────────────────────────────
# bge-small-en-v1.5 is only ~130 MB and very fast on CPU.
# Downloaded automatically from HuggingFace on first use.
_embeddings: Optional[HuggingFaceEmbeddings] = None

def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info(f"[RAG] Loading embedding model: {settings.EMBEDDING_MODEL}")
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},   # safe default; GPU optional
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


# ── ChromaDB Vector Store ──────────────────────────────────────────────────────
def get_vectorstore(collection_name: str = "aura_notes") -> Chroma:
    """Return a LangChain Chroma vectorstore backed by a local persistent directory."""
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )


# ── Document Ingestion ─────────────────────────────────────────────────────────
def ingest_file(file_path: str, metadata: Optional[dict] = None) -> int:
    """
    Load a PDF or .txt file, chunk it, embed it, and store in ChromaDB.

    Args:
        file_path: Absolute path to the uploaded file.
        metadata:  Optional dict of metadata to attach to each chunk
                   (e.g. {"subject": "DBMS", "user_id": 1}).

    Returns:
        Number of chunks added to the vector store.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"[RAG] Ingesting: {path.name}")

    # Load document
    if path.suffix.lower() == ".pdf":
        loader = PyPDFLoader(str(path))
    else:
        loader = TextLoader(str(path), encoding="utf-8")

    docs: list[Document] = loader.load()

    # Attach extra metadata
    if metadata:
        for doc in docs:
            doc.metadata.update(metadata)

    # Chunk the text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"[RAG] {path.name} → {len(chunks)} chunks")

    # Embed + store
    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    logger.info(f"[RAG] Stored {len(chunks)} chunks in ChromaDB")
    return len(chunks)


# ── Retrieval ──────────────────────────────────────────────────────────────────
def retrieve_context(query: str, user_filter: Optional[dict] = None, k: Optional[int] = None) -> list[Document]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Args:
        query:       The user's question.
        user_filter: Optional ChromaDB metadata filter (e.g. {"user_id": 1}).
        k:           Number of results (defaults to settings.RAG_TOP_K).

    Returns:
        List of LangChain Document objects.
    """
    k = k or settings.RAG_TOP_K
    vectorstore = get_vectorstore()

    if user_filter:
        return vectorstore.similarity_search(query, k=k, filter=user_filter)
    return vectorstore.similarity_search(query, k=k)


# ── RAG-enhanced LLM Response ─────────────────────────────────────────────────
RAG_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are AURA, a college study assistant. Use ONLY the following context from the "
            "student's notes to answer the question. If the answer is not in the context, "
            "say 'I could not find this in your uploaded notes.'\n\n"
            "--- Context ---\n{context}\n--- End Context ---"
        ),
    ),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])


def get_rag_response(
    question: str,
    history: list[dict],
    model_name: str,
    user_filter: Optional[dict] = None,
) -> tuple[str, list[str]]:
    """
    Full RAG pipeline: retrieve context → inject into prompt → LLM response.

    Returns:
        (response_text, list_of_source_filenames)
    """
    # 1. Retrieve relevant chunks
    docs = retrieve_context(question, user_filter=user_filter)
    if not docs:
        return (
            "I could not find anything relevant in your uploaded notes. "
            "Try uploading your notes first via the Documents section.",
            [],
        )

    context = "\n\n".join(doc.page_content for doc in docs)
    sources = list({doc.metadata.get("source", "unknown") for doc in docs})

    # 2. Convert history
    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))

    # 3. Build and invoke chain
    llm = ChatOllama(
        model=model_name,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.3,  # Lower temp for factual note retrieval
    )
    chain = RAG_PROMPT | llm | StrOutputParser()

    try:
        response = chain.invoke({
            "context": context,
            "question": question,
            "history": lc_history,
        })
        logger.info(f"[RAG] Retrieved {len(docs)} chunks from {len(sources)} sources")
        return response, sources
    except Exception as e:
        logger.error(f"[RAG] LLM error: {e}")
        return "⚠️ Could not generate a response from notes. Check Ollama is running.", []
