import tempfile
import streamlit as st
import os

from agents.ocr_agent import extract_text
from agents.language_agent import detect_language
from agents.classification_agent import classify_document
from agents.retrieval_agent import get_template
from agents.extraction_agent import extract_data
from agents.validation_agent import validate_json
from agents.confidence_agent import confidence_score

from exports.excel_export import export_excel

def upload_page():

    st.title("IDP Platform")

    file = st.file_uploader(
        "Upload Financial Document",
        type=[
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "tiff",
            "bmp",
            "webp"
        ]
    )

    if file:

        if st.button("Process"):

            file_ext = os.path.splitext(file.name)[1]

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=file_ext
            ) as tmp:

                tmp.write(file.read())
                file_path = tmp.name

            text = extract_text(file_path)

            language = detect_language(text)

            doc_type = classify_document(text)

            template = get_template(doc_type)

            extracted = extract_data(
                text,
                template
            )

            valid = validate_json(extracted)

            confidence = confidence_score(valid)

            st.subheader("Language")
            st.write(language)

            st.subheader("Document Type")
            st.write(doc_type)

            st.subheader("OCR Text")
            st.write(text)

            st.subheader("Extracted Data")
            st.json(extracted)

        
            st.subheader("Confidence")
            st.write(confidence)

            st.subheader("Raw LLM Response")
            st.code(extracted)

            excel = export_excel(extracted)

            with open(excel, "rb") as f:

                st.download_button(
                    "Download Excel",
                    f,
                    "output.xlsx"
                )