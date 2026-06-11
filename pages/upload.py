import streamlit as st
import tempfile
import os
import json

from agents.ocr_agent import extract_text
from agents.language_agent import detect_language
from agents.classification_agent import classify_document
from agents.retrieval_agent import get_template
from agents.extraction_agent import extract_data
from agents.validation_agent import validate_json
from agents.confidence_agent import confidence_score

from exports.excel_export import export_excel


def upload_page():

    st.title("📄 IDP Platform")

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

    if not file:
        return

    # Preview Images
    if file.type.startswith("image"):
        st.image(file, caption="Uploaded Image", width=400)

    # Export Mode
    export_mode = st.radio(
        "Export Mode",
        [
            "Create New Excel",
            "Append To Master Excel"
        ]
    )

    if st.button("Process"):

        try:

            # Save uploaded file temporarily
            file_ext = os.path.splitext(file.name)[1]

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=file_ext
            ) as tmp:

                tmp.write(file.read())
                file_path = tmp.name

            # OCR
            with st.spinner("Running OCR..."):

                text = extract_text(file_path)

            st.subheader("OCR Text")

            if not text.strip():

                st.error(
                    "No text detected in the document."
                )

                return

            st.text_area(
                "Extracted Text",
                text,
                height=250
            )

            # Language Detection
            language = detect_language(text)

            st.subheader("Language")
            st.success(language)

            # Document Classification
            with st.spinner(
                "Classifying document..."
            ):

                doc_type = classify_document(text)

            st.subheader("Document Type")
            st.success(doc_type)

            # Template Retrieval
            template = get_template(doc_type)

            # Extraction
            with st.spinner(
                "Extracting financial data..."
            ):

                extracted = extract_data(
                    text,
                    template
                )

            st.subheader("Raw LLM Response")
            st.code(extracted)

            # Validate JSON
            # Validate JSON
            validation = validate_json(extracted)

            confidence = confidence_score(validation)

            st.subheader("Confidence")
            st.metric(
                "Confidence Score",
                confidence
            )

            if not validation["valid"]:

                st.error("Validation Failed")

                for issue in validation["issues"]:
                    st.warning(issue)

                return

            # Convert to JSON
            try:

                extracted_json = json.loads(
                    extracted
                )

                st.subheader(
                    "Extracted Data"
                )

                st.json(extracted_json)

            except Exception as e:

                st.error(
                    f"JSON Parse Error: {e}"
                )

                st.code(extracted)

                return

            # Export
            excel_file = export_excel(
                extracted,
                export_mode
            )

            st.success(
                "Excel file generated successfully."
            )

            with open(
                excel_file,
                "rb"
            ) as f:

                st.download_button(
                    label="📥 Download Excel",
                    data=f,
                    file_name=os.path.basename(
                        excel_file
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:

            st.error(
                f"Processing Failed: {str(e)}"
            )