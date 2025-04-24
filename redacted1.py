from flask import Flask, request, send_file, jsonify
import fitz  # PyMuPDF
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
REDACTED_FOLDER = "redacted"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REDACTED_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF Redaction Tool</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin: 20px; }
            input, button { padding: 10px; margin: 10px; }
            textarea { width: 80%; height: 100px; }
            embed { width: 80%; height: 500px; margin-top: 20px; border: 1px solid #ddd; }
        </style>
    </head>
    <body>

        <h1>PDF Redaction Tool</h1>
        <input type="file" id="fileInput" accept=".pdf"><br>
        <button onclick="uploadFile()">Upload PDF</button>

        <h3>Enter words to redact:</h3>
        <textarea id="redactWords" placeholder="Type words separated by commas..."></textarea><br>
        <button onclick="startListening()">🎤 Speak</button>
        <button onclick="applyRedaction()">📝 Apply Redaction</button>
        <button id="downloadBtn" style="display:none;" onclick="downloadRedacted()">📄 Download Redacted PDF</button>

        <embed id="pdfViewer" type="application/pdf" style="display:none;" />

        <script>
            let uploadedFilename = "";

            async function uploadFile() {
                const fileInput = document.getElementById('fileInput').files[0];
                if (!fileInput) {
                    alert("Please select a file.");
                    return;
                }

                let formData = new FormData();
                formData.append("file", fileInput);

                let response = await fetch("/upload", {
                    method: "POST",
                    body: formData
                });

                let result = await response.json();
                if (result.message) {
                    uploadedFilename = result.filename;
                    alert("File uploaded successfully.");
                    document.getElementById("pdfViewer").src = result.preview_url;
                    document.getElementById("pdfViewer").style.display = "block";
                }
            }

            async function applyRedaction() {
                if (!uploadedFilename) {
                    alert("Please upload a PDF first.");
                    return;
                }

                let words = document.getElementById("redactWords").value;
                if (!words.trim()) {
                    alert("Enter words to redact.");
                    return;
                }

                let response = await fetch("/redact", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ filename: uploadedFilename, words: words })
                });

                let result = await response.json();
                if (result.message) {
                    alert("Redaction applied!");
                    document.getElementById("downloadBtn").style.display = "inline";
                    document.getElementById("downloadBtn").dataset.filename = result.redacted_filename;
                }
            }

            function downloadRedacted() {
                let filename = document.getElementById("downloadBtn").dataset.filename;
                window.location.href = "/download/" + filename;
            }

            function startListening() {
                if (!('webkitSpeechRecognition' in window)) {
                    alert("Speech recognition not supported in your browser.");
                    return;
                }

                const recognition = new webkitSpeechRecognition();
                recognition.lang = "en-US";
                recognition.onresult = function(event) {
                    let spokenWord = event.results[0][0].transcript.trim();
                    let currentWords = document.getElementById('redactWords').value;
                    document.getElementById('redactWords').value = currentWords ? `${currentWords}, ${spokenWord}` : spokenWord;
                };
                recognition.start();
            }
        </script>

    </body>
    </html>
    """

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    return jsonify({
        "message": "File uploaded",
        "filename": file.filename,
        "preview_url": f"/view/{file.filename}"
    })

@app.route("/view/<filename>")
def view_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path)

@app.route("/redact", methods=["POST"])
def redact():
    data = request.json
    filename = data["filename"]
    words_to_redact = [w.strip() for w in data["words"].split(",") if w.strip()]

    input_pdf = os.path.join(UPLOAD_FOLDER, filename)
    output_pdf = os.path.join(REDACTED_FOLDER, f"redacted_{filename}")

    if not os.path.exists(input_pdf):
        return jsonify({"error": "File not found"}), 400

    doc = fitz.open(input_pdf)
    for page in doc:
        for word in words_to_redact:
            areas = page.search_for(word)
            for area in areas:
                page.add_redact_annot(area, fill=(0, 0, 0))
        page.apply_redactions()

    doc.save(output_pdf)
    return jsonify({"message": "Redaction applied", "redacted_filename": f"redacted_{filename}"})

@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(REDACTED_FOLDER, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
