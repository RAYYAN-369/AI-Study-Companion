from pypdf import PdfReader


def extract_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.
    """

    text = ""

    reader = PdfReader(file_path)

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def extract_txt(file_path: str) -> str:
    """
    Extract text from a TXT file.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def extract_text(file_path: str):
    """
    Detect file type and extract text.
    """

    if file_path.endswith(".pdf"):
        return extract_pdf(file_path)

    elif file_path.endswith(".txt"):
        return extract_txt(file_path)

    else:
        raise ValueError("Unsupported file format.")