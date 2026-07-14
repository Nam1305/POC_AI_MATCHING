"""
TF-IDF + cosine similarity scoring — a lightweight, non-LLM alternative to
the embedding-based /ai/score pipeline. Ranks raw CV text against raw JD
text using classic bag-of-words TF-IDF vectors.
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def rank_cvs_tfidf(jd_text: str, cv_texts: list[str]) -> list[float]:
    """
    Score each CV's raw text against the JD's raw text via TF-IDF cosine
    similarity. Returns a 0-100 score per CV, in the same order as cv_texts.

    The JD and all CVs are fit into a single TF-IDF vocabulary so their
    vectors are directly comparable.
    """
    documents = [jd_text] + cv_texts
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(documents)

    jd_vector = tfidf_matrix[0:1]
    cv_vectors = tfidf_matrix[1:]
    similarities = cosine_similarity(jd_vector, cv_vectors)[0]

    return [round(float(s) * 100, 2) for s in similarities]
