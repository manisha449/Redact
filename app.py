from flask import Flask, request, send_file, render_template
import fitz  # PyMuPDF for PDF redaction
import mammoth  # For extracting text from DOCX
import re
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Redacts text in PDF using black boxes
def redact_pdf(input_pdf, words_to_redact):
    doc = fitz.open(input_pdf)
    for page in doc:
        for word in words_to_redact:
            word = word.strip()
            if word.lower() == "phone":
                pattern = re.compile(r"\b\d{10}\b")
                matches = page.search_for(pattern)
                for inst in matches:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
            elif word.lower() == "email":
                pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
                matches = page.search_for(pattern)
                for inst in matches:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
            elif word.lower() == "aadhaar":
                pattern = re.compile(r"\b\d{4} \d{4} \d{4}\b")
                matches = page.search_for(pattern)
                for inst in matches:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
            elif word.lower() == "salary":
                page.search_for("salary")
                matches = page.search_for("salary")
                for inst in matches:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
            else:
                matches = page.search_for(word)
                for inst in matches:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
        page.apply_redactions()

    output_pdf = os.path.join(UPLOAD_FOLDER, "redacted.pdf")
    doc.save(output_pdf)
    return output_pdf

# Redacts text in DOCX by replacing content
def redact_docx(input_docx, words_to_redact):
    with open(input_docx, "rb") as f:
        result = mammoth.extract_raw_text(f)

    text = result.value
    for word in words_to_redact:
        word = word.strip()
        if word.lower() == "phone":
            text = re.sub(r"\b\d{10}\b", "[REDACTED]", text)
        elif word.lower() == "email":
            text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED]", text)
        elif word.lower() == "aadhaar":
            text = re.sub(r"\b\d{4} \d{4} \d{4}\b", "[REDACTED]", text)
        elif word.lower() == "salary":
            text = re.sub(r"salary", "[REDACTED]", text, flags=re.IGNORECASE)
        else:
            text = text.replace(word, "[REDACTED]")

    output_docx = os.path.join(UPLOAD_FOLDER, "redacted.docx")
    with open(output_docx, "w", encoding="utf-8") as f:
        f.write(text)

    return output_docx

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files["file"]
        redact_words = request.form["redact_words"].split(",")

        if uploaded_file:
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(file_path)

            if uploaded_file.filename.endswith(".pdf"):
                redacted_file = redact_pdf(file_path, redact_words)
            elif uploaded_file.filename.endswith(".docx"):
                redacted_file = redact_docx(file_path, redact_words)
            else:
                return "Unsupported file type."

            return send_file(redacted_file, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
