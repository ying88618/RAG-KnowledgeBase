from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=120,
)


def split(text: str) -> list[str]:
    return _splitter.split_text(text)
