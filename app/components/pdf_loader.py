import os
import glob as glob_module
import fitz  # PyMuPDF
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.common.logger import get_logger
from app.common.custom_exception import CustomException

from app.config.config import DATA_PATH,CHUNK_SIZE,CHUNK_OVERLAP

logger = get_logger(__name__)

import re

# Valid Roman numeral pattern (I, II, III, IV, V, ... XXVII, etc.)
_ROMAN_RE = re.compile(r'^(M{0,3})(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$')

def _is_roman_numeral(s: str) -> bool:
    """Check if a string is a valid Roman numeral."""
    return bool(_ROMAN_RE.match(s.upper())) and len(s) > 0

def _build_page_label_map(pdf_path: str) -> dict:
    """
    Build a mapping from physical page index (0-based) to the real
    printed page number by extracting it from the page text itself.
    
    The GALE Encyclopedia pages have a footer pattern like:
        'GALE ENCYCLOPEDIA OF MEDICINE 2' with a nearby page number.
    Content pages have Arabic numbers (625, 626, ...).
    Front matter pages have Roman numerals (IX, XI, XIII, ...).
    Title/copyright pages with no number get labeled as 'unnumbered'.
    """
    label_map = {}
    try:
        doc = fitz.open(pdf_path)
        for i in range(len(doc)):
            text = doc[i].get_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            printed_page = None
            # Search from the BOTTOM of the page upward for 'GALE ENCYCLOPEDIA'
            # This avoids matching body-text references to the encyclopedia name
            for j in range(len(lines) - 1, -1, -1):
                if 'GALE ENCYCLOPEDIA' in lines[j].upper():
                    # Check nearby lines (within 2 lines) for a page number
                    # Prefer Arabic numbers first, then Roman numerals
                    arabic = None
                    roman = None
                    for k in range(max(0, j - 2), min(len(lines), j + 3)):
                        candidate = lines[k].strip()
                        if candidate.isdigit():
                            arabic = candidate
                        elif _is_roman_numeral(candidate) and not candidate.isalpha() or (len(candidate) > 1 and _is_roman_numeral(candidate)):
                            # Only treat single letters as Roman if they are 
                            # common Roman page numbers (I, V, X), not section headers (C, D, M)
                            if len(candidate) == 1 and candidate.upper() in ('C', 'D', 'M', 'L'):
                                continue  # Skip — likely a section header letter
                            roman = candidate.lower()
                    
                    printed_page = arabic or roman
                    break  # Stop after finding the bottom-most GALE ENCYCLOPEDIA
            
            if printed_page:
                label_map[i] = printed_page
            else:
                label_map[i] = "unnumbered"
        
        doc.close()
        logger.info(f"Built page label map for {len(label_map)} pages from {pdf_path}")
    except Exception as e:
        logger.warning(f"Could not build page label map from {pdf_path}: {e}")
    return label_map

def load_pdf_files():
    try:
        if not os.path.exists(DATA_PATH):
            raise CustomException("Data path doesnt exist")
        
        logger.info(f"Loading files from {DATA_PATH}")

        pdf_files = glob_module.glob(os.path.join(DATA_PATH, "*.pdf"))

        if not pdf_files:
            logger.warning("No pdfs were found")
            return []

        all_documents = []

        for pdf_path in pdf_files:
            logger.info(f"Loading: {pdf_path}")

            # Build real page label map using PyMuPDF
            label_map = _build_page_label_map(pdf_path)

            loader = PyPDFLoader(pdf_path)
            docs = loader.load()

            # Override the 'page' metadata with the real printed page label
            for doc in docs:
                physical_index = doc.metadata.get("page", 0)  # 0-based from PyPDFLoader
                real_label = label_map.get(physical_index, str(physical_index + 1))
                doc.metadata["page"] = real_label
                doc.metadata["physical_page"] = physical_index

            all_documents.extend(docs)

        logger.info(f"Successfully fetched {len(all_documents)} pages from {len(pdf_files)} PDF(s)")
        return all_documents
    
    except Exception as e:
        error_message = CustomException("Failed to load PDF" , e)
        logger.error(str(error_message))
        return []
    

def create_text_chunks(documents):
    try:
        if not documents:
            raise CustomException("No documents were found")
        
        logger.info(f"Splitting {len(documents)} documents into chunks")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,chunk_overlap=CHUNK_OVERLAP)

        text_chunks = text_splitter.split_documents(documents)

        logger.info(f"Generated {len(text_chunks)} text chunks")
        return text_chunks
    
    except Exception as e:
        error_message = CustomException("Failed to generate chunks" , e)
        logger.error(str(error_message))
        return []





