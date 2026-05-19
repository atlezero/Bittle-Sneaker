"""
rag_engine.py — Simple keyword-based RAG (Retrieval-Augmented Generation) engine.

ใช้ TF-IDF + cosine similarity ในการค้นหา context chunk ที่เกี่ยวข้องที่สุด
จาก knowledge base ที่เป็นไฟล์ .txt โดยไม่ต้องพึ่ง external embedding service.
"""

from __future__ import annotations

import math
import re
from pathlib import Path


class RAGEngine:
    """
    Simple retrieval engine ที่แบ่ง knowledge file ออกเป็น chunks
    แล้วค้นหาด้วย TF-IDF cosine similarity.
    """

    def __init__(self, knowledge_path: str, chunk_size: int = 200) -> None:
        """
        Args:
            knowledge_path: path ไปยังไฟล์ .txt ที่เป็น knowledge base
            chunk_size: จำนวนตัวอักษรโดยประมาณต่อ chunk (default 200)
        """
        path = Path(knowledge_path)
        if not path.exists():
            raise FileNotFoundError(
                f"ไม่พบไฟล์ knowledge base: {knowledge_path}"
            )

        text = path.read_text(encoding="utf-8")
        self._chunks: list[str] = self._split_chunks(text, chunk_size)

        if not self._chunks:
            raise ValueError(
                f"ไฟล์ {knowledge_path} ว่างเปล่า ไม่มีข้อมูลให้ค้นหา"
            )

        # Pre-compute TF-IDF vectors for all chunks
        self._tf_idf_matrix = self._build_tfidf(self._chunks)

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """
        ค้นหา chunk ที่เกี่ยวข้องกับ query มากที่สุด

        Returns:
            list ของ chunk strings เรียงจากคะแนนสูงสุด
        """
        query_vec = self._tfidf_vector(self._tokenize(query), self._idf)
        scores = [
            self._cosine(query_vec, chunk_vec)
            for chunk_vec in self._tf_idf_matrix
        ]

        # Sort by score descending, take top_k
        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )
        results = [
            self._chunks[idx]
            for idx, score in ranked[:top_k]
            if score > 0  # ไม่เอา chunk ที่ไม่เกี่ยวข้องเลย
        ]

        # ถ้าไม่มี chunk ที่ตรงเลย ส่งกลับ chunk แรก ๆ แทน
        if not results:
            results = self._chunks[:top_k]

        return results

    @property
    def chunk_count(self) -> int:
        """จำนวน chunk ทั้งหมดใน knowledge base"""
        return len(self._chunks)

    # ──────────────────────────────────────────────
    # Chunking
    # ──────────────────────────────────────────────

    @staticmethod
    def _split_chunks(text: str, chunk_size: int) -> list[str]:
        """
        แบ่ง text เป็น chunks โดย:
        1. ลองแบ่งตาม paragraph (บรรทัดว่าง) ก่อน
        2. ถ้า paragraph ยาวเกิน chunk_size ให้แบ่งอีกรอบตามประโยค
        """
        # แบ่งตาม double newline (paragraph)
        paragraphs = re.split(r"\n\s*\n", text.strip())
        chunks: list[str] = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(para) <= chunk_size * 2:
                chunks.append(para)
            else:
                # แบ่งตามประโยค (. ! ?)
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) <= chunk_size:
                        current = (current + " " + sent).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
                if current:
                    chunks.append(current)

        return chunks

    # ──────────────────────────────────────────────
    # TF-IDF
    # ──────────────────────────────────────────────

    def _build_tfidf(
        self, chunks: list[str]
    ) -> list[dict[str, float]]:
        """สร้าง TF-IDF vector สำหรับทุก chunk"""
        tokenized = [self._tokenize(c) for c in chunks]
        self._idf = self._compute_idf(tokenized)
        return [self._tfidf_vector(tokens, self._idf) for tokens in tokenized]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """แบ่งคำอย่างง่าย: lowercase + แยกตัวอักษรและตัวเลข"""
        text = text.lower()
        # จัดการทั้ง ASCII word และ Unicode (เช่น ภาษาไทย) แบบ char-level bigram
        ascii_words = re.findall(r"[a-z0-9]+", text)
        # สำหรับภาษาไทย ใช้ unigram character เพื่อให้พอจับคำได้บ้าง
        thai_chars = re.findall(r"[\u0e00-\u0e7f]+", text)
        thai_bigrams = [
            word[i : i + 2]
            for word in thai_chars
            for i in range(len(word) - 1)
        ]
        return ascii_words + thai_bigrams

    @staticmethod
    def _compute_idf(tokenized_docs: list[list[str]]) -> dict[str, float]:
        """คำนวณ IDF สำหรับ vocabulary ทั้งหมด"""
        n = len(tokenized_docs)
        df: dict[str, int] = {}
        for tokens in tokenized_docs:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        return {
            token: math.log((n + 1) / (freq + 1)) + 1
            for token, freq in df.items()
        }

    @staticmethod
    def _tfidf_vector(
        tokens: list[str], idf: dict[str, float]
    ) -> dict[str, float]:
        """สร้าง TF-IDF vector จาก token list"""
        if not tokens:
            return {}
        tf: dict[str, float] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        n = len(tokens)
        return {
            token: (count / n) * idf.get(token, 1.0)
            for token, count in tf.items()
        }

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        """คำนวณ cosine similarity ระหว่าง 2 sparse vectors"""
        if not a or not b:
            return 0.0
        dot = sum(a.get(k, 0.0) * v for k, v in b.items())
        mag_a = math.sqrt(sum(v * v for v in a.values()))
        mag_b = math.sqrt(sum(v * v for v in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
