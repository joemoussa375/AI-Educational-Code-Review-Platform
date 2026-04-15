import sys

try:
    from docx import Document
except ImportError:
    print("python-docx is not installed. Please install it using 'pip install python-docx'")
    sys.exit(1)

def main():
    txt_path = "Academic_Paper_Revised.txt"
    docx_path = "Academic_Paper_Revised.docx"

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {txt_path}")
        sys.exit(1)

    doc = Document()
    
    # Split the text by double newlines to maintain paragraphs
    # rather than putting everything in one giant block or having every line be a paragraph.
    paragraphs = content.split("\n\n")
    for para in paragraphs:
        clean_para = para.strip()
        if clean_para:
            doc.add_paragraph(clean_para)

    doc.save(docx_path)
    print(f"Successfully created {docx_path}!")

if __name__ == "__main__":
    main()
