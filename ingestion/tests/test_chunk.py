from ingestion.chunk import chunk_text


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("One short paragraph.") == ["One short paragraph."]


def test_chunks_respect_max_size_and_cover_all_text() -> None:
    sentences = [f"Sentence number {i} explains a step of applying pressure." for i in range(60)]
    text = "\n\n".join(" ".join(sentences[i : i + 5]) for i in range(0, 60, 5))

    chunks = chunk_text(text, max_chars=300, overlap=50)

    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
    joined = " ".join(chunks)
    assert all(s in joined for s in sentences)


def test_consecutive_chunks_overlap() -> None:
    text = "\n\n".join(f"Paragraph {i} has several words about the point." for i in range(20))
    chunks = chunk_text(text, max_chars=200, overlap=60)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.split()[0] in previous


def test_very_long_sentence_is_split() -> None:
    chunks = chunk_text("x" * 2500, max_chars=1000, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    assert sum(c.count("x") for c in chunks) >= 2500
