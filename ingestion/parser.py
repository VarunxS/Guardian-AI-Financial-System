"""
Statement parser — handles CSV bank statements and PDF credit card / UPI statements.
Supports SBI, HDFC, ICICI, Axis formats.
"""
from __future__ import annotations

import re
import logging
from datetime import datetime
from uuid import uuid4

from ingestion.schema import Transaction, StatementUpload

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category keyword mapping
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, str] = {
    # Food & Dining
    "zomato": "food_dining",
    "swiggy": "food_dining",
    "dominos": "food_dining",
    "mcdonalds": "food_dining",
    "pizza hut": "food_dining",
    "burger king": "food_dining",
    "starbucks": "food_dining",
    "restaurant": "food_dining",
    "cafe": "food_dining",
    "food": "food_dining",
    "dining": "food_dining",
    # Groceries
    "bigbasket": "groceries",
    "blinkit": "groceries",
    "zepto": "groceries",
    "dmart": "groceries",
    "reliance fresh": "groceries",
    "grofers": "groceries",
    "grocery": "groceries",
    "supermarket": "groceries",
    "more supermarket": "groceries",
    # Entertainment & Streaming
    "netflix": "streaming",
    "spotify": "streaming",
    "hotstar": "streaming",
    "disney": "streaming",
    "amazon prime": "streaming",
    "prime video": "streaming",
    "sonyliv": "streaming",
    "jio cinema": "streaming",
    "youtube premium": "streaming",
    "apple music": "streaming",
    "zee5": "streaming",
    "audible": "streaming",
    "pvr": "entertainment",
    "inox": "entertainment",
    "bookmyshow": "entertainment",
    # Travel
    "ola": "travel",
    "uber": "travel",
    "rapido": "travel",
    "irctc": "travel",
    "makemytrip": "travel",
    "cleartrip": "travel",
    "goibibo": "travel",
    "indigo": "travel",
    "air india": "travel",
    "vistara": "travel",
    "spicejet": "travel",
    # Fuel
    "petrol": "fuel",
    "diesel": "fuel",
    "bpcl": "fuel",
    "hpcl": "fuel",
    "iocl": "fuel",
    "indian oil": "fuel",
    "shell": "fuel",
    "fuel": "fuel",
    # Shopping
    "amazon": "shopping",
    "flipkart": "shopping",
    "myntra": "shopping",
    "ajio": "shopping",
    "nykaa": "shopping",
    "tata cliq": "shopping",
    "meesho": "shopping",
    "croma": "shopping",
    "reliance digital": "shopping",
    # Health
    "gym": "health",
    "pharmacy": "health",
    "apollo": "health",
    "practo": "health",
    "1mg": "health",
    "pharmeasy": "health",
    "medplus": "health",
    "hospital": "health",
    "doctor": "health",
    "cult.fit": "health",
    "cultfit": "health",
    "headspace": "health",
    # Utilities
    "electricity": "utilities",
    "water bill": "utilities",
    "gas bill": "utilities",
    "broadband": "utilities",
    "airtel": "utilities",
    "jio": "utilities",
    "vodafone": "utilities",
    "vi ": "utilities",
    "bsnl": "utilities",
    "tata power": "utilities",
    "mahanagar gas": "utilities",
    # EMI & Loans
    "emi": "emi_loan",
    "loan": "emi_loan",
    "bajaj finserv": "emi_loan",
    "hdfc ltd": "emi_loan",
    "home loan": "emi_loan",
    # Insurance
    "insurance": "insurance",
    "lic": "insurance",
    "policy": "insurance",
    "icici prudential": "insurance",
    "hdfc life": "insurance",
    "star health": "insurance",
    # Investment
    "mutual fund": "investment",
    "sip": "investment",
    "zerodha": "investment",
    "groww": "investment",
    "kuvera": "investment",
    "coin": "investment",
    "nps": "investment",
    "ppf": "investment",
    # Transfers
    "neft": "transfer",
    "rtgs": "transfer",
    "imps": "transfer",
    "upi": "transfer",
    "transfer": "transfer",
    "google pay": "transfer",
    "phonepe": "transfer",
    "paytm": "transfer",
    # Subscription (generic)
    "subscription": "subscription",
    "membership": "subscription",
    "linkedin": "subscription",
    "notion": "subscription",
    "slack": "subscription",
    "github": "subscription",
    "figma": "subscription",
    "canva": "subscription",
    "dream11": "subscription",
    # Lifestyle & Others
    "rent": "rent_maintenance",
    "house": "rent_maintenance",
    "maid": "rent_maintenance",
    "cook": "rent_maintenance",
    "society": "rent_maintenance",
    "maintenance": "rent_maintenance",
    "school": "education",
    "fee": "education",
    "college": "education",
    "tutor": "education",
    "cash": "cash_withdrawal",
    "withdrawal": "cash_withdrawal",
    "atm": "atm_withdrawal",
}


class StatementParser:
    """Parses bank CSV and credit card / UPI PDF statements into Transaction objects."""

    def parse(self, file_path: str, source: str, user_id: str = "default", api_key: str = None, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> StatementUpload:
        """Route to the correct parser based on source type. Falls back to LLM for tricky PDFs."""
        if source == "bank_csv":
            transactions = self._parse_bank_csv(file_path)
            # LLM Fallback for tricky CSVs
            if not transactions and api_key:
                logger.info(f"[Parser] CSV patterns failed. Attempting LLM extraction...")
                transactions = self._parse_with_llm(file_path, api_key, provider, model_id)
        elif source in ("credit_card_pdf", "upi_pdf"):
            transactions = self._parse_pdf(file_path)
            
            # Deep Fallback: If pattern-matching failed but we have an API key, use LLM
            if not transactions and api_key:
                logger.info(f"[Parser] Patterns failed for {source}. Attempting LLM extraction...")
                transactions = self._parse_with_llm(file_path, api_key, provider, model_id)
        else:
            raise ValueError(
                f"Unrecognised source type: '{source}'. "
                f"Must be one of: bank_csv, credit_card_pdf, upi_pdf"
            )

        # Step 4: Refine 'Other' categories using LLM if available
        if api_key and transactions:
            others = [t for t in transactions if t.category == "other"]
            if len(others) > 5:
                logger.info(f"[Parser] Detected {len(others)} 'other' transactions. Categorizing via LLM...")
                refined = self._batch_categorise_with_llm(others, api_key, provider, model_id)
                # Map back by ID
                id_map = {t.transaction_id: t.category for t in refined}
                for t in transactions:
                    if t.transaction_id in id_map:
                        t.category = id_map[t.transaction_id]

        return StatementUpload(
            user_id=user_id,
            source=source,
            transactions=transactions,
        )

    # ------------------------------------------------------------------
    # Universal CSV parser (Heuristic Detection)
    # ------------------------------------------------------------------
    def _parse_bank_csv(self, file_path: str) -> list[Transaction]:
        """
        Universal CSV Parser with enhanced encoding and header detection.
        """
        import pandas as pd

        df = None
        # Try different common encodings
        for encoding in ["utf-8", "latin-1", "iso-8859-1", "cp1252"]:
            if df is not None: break
            for skip in range(20):
                try:
                    temp_df = pd.read_csv(file_path, skiprows=skip, skipinitialspace=True, encoding=encoding)
                    if len(temp_df.columns) >= 3 and len(temp_df) > 0:
                        cols_str = " ".join([str(c).lower() for c in temp_df.columns])
                        # Broader keyword set for Indian banks
                        keywords = ["date", "desc", "narration", "particular", "amount", "debit", "txn", "details", "ref", "value"]
                        if any(x in cols_str for x in keywords):
                            df = temp_df
                            break
                except Exception:
                    continue
        
        if df is None:
            try:
                df = pd.read_csv(file_path, skipinitialspace=True, encoding="utf-8")
            except:
                df = pd.read_csv(file_path, skipinitialspace=True, encoding="latin-1")

        df.columns = [str(c).strip().lower() for c in df.columns]

        # Step 2: Heuristic Column Identification (Enhanced)
        identified = {"date": None, "desc": None, "debit": None, "credit": None, "amount": None}
        
        name_map = {
            "date": ["date", "txn date", "transaction date", "value date", "posting date", "transaction_date", "trans date"],
            "desc": ["description", "narration", "particulars", "details", "remarks", "transaction remarks", "remittance info"],
            "debit": ["debit", "withdrawal", "withdrawal amt", "dr", "debit amount", "paid out"],
            "credit": ["credit", "deposit", "deposit amt", "cr", "credit amount", "paid in"],
            "amount": ["amount", "txn amount", "transaction amount", "amount (inr)", "net amount", "total amount"]
        }

        for target, keywords in name_map.items():
            for col in df.columns:
                if any(kw == col or f" {kw} " in f" {col} " for kw in keywords):
                    identified[target] = col
                    break

        # Data-pattern fallback for missing critical columns
        if not identified["date"] or (not identified["amount"] and not identified["debit"]):
            for col in df.columns:
                sample = df[col].dropna().head(5).astype(str).tolist()
                if not sample: continue
                if not identified["date"] and any(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', s) for s in sample):
                    identified["date"] = col
                elif not identified["amount"] and any(re.sub(r'[^\d.]', '', s).replace('.','',1).isdigit() for s in sample):
                    identified["amount"] = col

        if not identified["date"] or (not identified["desc"] and len(df.columns) < 2):
            logger.warning(f"Could not identify required columns in CSV: {list(df.columns)}")
            return []

        # Step 3: Transaction Extraction
        transactions: list[Transaction] = []
        for _, row in df.iterrows():
            try:
                txn_date = self._parse_date(str(row[identified["date"]]))
                if not txn_date: continue

                description = str(row[identified["desc"]]) if identified["desc"] else "Unknown"
                if "nan" in description.lower(): description = "Unknown"

                amount = 0.0
                if identified["debit"] and identified["credit"]:
                    d = self._clean_amount(str(row[identified["debit"]]))
                    c = self._clean_amount(str(row[identified["credit"]]))
                    amount = d if d != 0 else -c
                elif identified["amount"]:
                    raw_amt = str(row[identified["amount"]])
                    amount = self._clean_amount(raw_amt)
                    if "cr" in raw_amt.lower(): amount = -abs(amount)
                    if "dr" in raw_amt.lower(): amount = abs(amount)
                
                if amount == 0 and not identified["amount"]: continue

                transactions.append(
                    Transaction(
                        date=txn_date,
                        description=description,
                        amount=amount,
                        category=self._categorise(description),
                        merchant_name=self._clean_merchant(description),
                        transaction_id=str(uuid4()),
                    )
                )
            except Exception:
                continue

        return transactions

    def _clean_amount(self, amt_str: str) -> float:
        """Strip non-numeric characters (except . and -) and return float."""
        try:
            cleaned = re.sub(r'[^\d.-]', '', amt_str)
            return float(cleaned) if (cleaned and cleaned != "-") else 0.0
        except ValueError:
            return 0.0

    def _parse_with_llm(self, file_path: str, api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> list[Transaction]:
        """Extract transactions from PDF text using an LLM (OpenAI/Gemini)."""
        try:
            import fitz  # PyMuPDF

            # Extract raw text (handle both PDF and plain text/CSV)
            raw_text = ""
            if file_path.lower().endswith(".pdf"):
                try:
                    doc = fitz.open(file_path)
                    for page in doc:
                        raw_text += page.get_text() + "\n"
                    doc.close()
                except Exception:
                    pass
            
            # If not a PDF or PDF extraction failed, try plain text
            if not raw_text.strip():
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        raw_text = f.read()
                except Exception:
                    pass

            if not raw_text.strip():
                return []

            from agents.utils import get_llm
            from langchain_core.messages import SystemMessage, HumanMessage
            import json

            llm = get_llm(api_key=api_key, provider=provider, model_id=model_id)
            system = (
                "You are a financial data extractor. Extract every single transaction from the bank/UPI statement text provided. "
                "Return a JSON list of objects with keys: 'date' (YYYY-MM-DD), 'description' (merchant name), 'amount' (float, positive for debit, negative for credit). "
                "If it is a single receipt, return a list with one item. Return ONLY valid JSON."
            )
            prompt = f"Statement Text:\n{raw_text[:8000]}" # Truncate if too long
            
            response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
            text = response.content.strip()
            
            # Clean JSON markdown if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            txns = []
            for item in data:
                try:
                    desc = item.get("description", "Unknown")
                    txns.append(Transaction(
                        date=datetime.strptime(item["date"], "%Y-%m-%d"),
                        description=desc,
                        amount=float(item["amount"]),
                        category=self._categorise(desc),
                        merchant_name=self._clean_merchant(desc),
                        transaction_id=str(uuid4())
                    ))
                except Exception:
                    continue
            return txns
        except Exception as e:
            logger.error(f"[Parser] LLM extraction failed: {e}")
            return []

    # ------------------------------------------------------------------
    # PDF parser (credit card / UPI statements)
    # ------------------------------------------------------------------
    def _parse_pdf(self, file_path: str) -> list[Transaction]:
        """Parse a PDF statement — handles multi-row statements and single receipts."""
        transactions = self._parse_pdf_tables(file_path)
        
        # If no table found, it might be a single receipt (GPay/PhonePe/Paytm)
        if not transactions:
            transactions = self._parse_pdf_text(file_path)
            
        # Final cleanup and deduplication
        unique_txns = []
        seen = set()
        for t in transactions:
            key = f"{t.date.isoformat()}-{t.amount}-{t.description[:30]}"
            if key not in seen:
                unique_txns.append(t)
                seen.add(key)
                
        return unique_txns

    def _parse_pdf_tables(self, file_path: str) -> list[Transaction]:
        """
        Extract transactions from PDF tables using pdfplumber.
        Enhanced with better line detection and encryption handling.
        """
        import pdfplumber

        transactions: list[Transaction] = []
        try:
            # Settings to handle receipts/statements without clear borders
            table_settings = {
                "vertical_strategy": "text", 
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
            }
            with pdfplumber.open(file_path) as pdf:
                if pdf.is_encrypted:
                    # Logging this would be ideal, but for now we throw to catch in outer loop
                    raise ValueError("PDF is password-protected. Please unlock it before uploading.")

                for page in pdf.pages:
                    tables = page.extract_tables()
                    # If standard extraction failed, try text-based vertical alignment
                    if not tables or len(tables[0]) < 2:
                        tables = page.extract_tables(table_settings)
                        
                    for table in tables:
                        if not table: continue
                        for row in table:
                            if not row or len(row) < 2: continue
                            txn = self._row_to_transaction(row)
                            if txn: transactions.append(txn)
        except ValueError as ve:
            # Re-raise password error
            raise ve
        except Exception:
            pass
        return transactions

    def _parse_pdf_text(self, file_path: str) -> list[Transaction]:
        """Fall back: extract transactions from raw PDF text using PyMuPDF."""
        import fitz  # PyMuPDF

        transactions: list[Transaction] = []
        try:
            doc = fitz.open(file_path)
            if doc.is_encrypted:
                return [] # Already caught by tables or will be caught later

            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            doc.close()

            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            
            # Single Receipt Logic: Flexible search for common Indian UPI receipts (GPay, PhonePe, Paytm, etc)
            if len(lines) < 100:
                # 1. Look for Date (various formats: DD MMM YYYY, DD/MM/YYYY, etc)
                date_patterns = [
                    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
                    r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
                    r"(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})"
                ]
                dt = None
                for p in date_patterns:
                    date_match = re.search(p, full_text, re.IGNORECASE)
                    if date_match:
                        dt = self._parse_date(date_match.group(1))
                        if dt: break
                
                # 2. Look for Amount (highly flexible)
                # Matches: ₹ 500.00, INR 500, Amount: 500, Paid: 500
                amount_match = re.search(r"(?:Total|Amount|Paid|₹|INR)\s*:?\s*[₹\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", full_text, re.IGNORECASE)
                
                if dt and amount_match:
                    amt = float(amount_match.group(1).replace(",", ""))
                    if amt > 0:
                        # 3. Look for Merchant/Payee
                        # Usually follows 'To', 'Paid to', or 'Merchant'
                        merchant_match = re.search(r"(?:To|Paid to|Merchant|Paying to|Transfer to)\s*:?\s*([^\n]+)", full_text, re.IGNORECASE)
                        desc = merchant_match.group(1).strip() if merchant_match else "UPI Payment"
                        # Clean common garbage from merchant name (bank refs, ac/nos)
                        desc = re.sub(r"(?:Bank|A/c|XXXX|Ref|Id|@\w+).*", "", desc, flags=re.IGNORECASE).strip()
                        desc = re.sub(r"\s+", " ", desc)
                        
                        transactions.append(Transaction(
                            date=dt,
                            description=desc,
                            amount=amt,
                            category=self._categorise(desc),
                            merchant_name=self._clean_merchant(desc),
                            transaction_id=str(uuid4())
                        ))
                        return transactions

            # Standard multi-line fallback for older statements
            for line in lines:
                txn = self._line_to_transaction(line)
                if txn: transactions.append(txn)
        except Exception:
            pass
        return transactions

    def _row_to_transaction(self, row: list) -> Transaction | None:
        """Try to parse a table row into a Transaction."""
        try:
            # Typical row: [date, description, debit/credit, amount, balance]
            date_str = str(row[0]).strip() if row[0] else ""
            date = self._parse_date(date_str)
            if date is None:
                return None

            description = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            if not description:
                return None

            # Find the amount — try columns from index 2 onwards
            amount = 0.0
            for cell in row[2:]:
                try:
                    cleaned = re.sub(r"[₹,\s]", "", str(cell).strip())
                    if cleaned and cleaned not in ("", "-", "nan"):
                        val = float(cleaned)
                        if val != 0:
                            amount = val
                            break
                except (ValueError, TypeError):
                    continue

            merchant = self._clean_merchant(description)
            category = self._categorise(description)

            return Transaction(
                date=date,
                description=description,
                amount=amount,
                category=category,
                merchant_name=merchant,
                transaction_id=str(uuid4()),
            )
        except Exception:
            return None

    def _line_to_transaction(self, line: str) -> Transaction | None:
        """Try to parse a raw text line into a Transaction."""
        # Pattern: date at the start, amount somewhere with ₹ or digits
        date_pattern = r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{1,2}\s+\w{3}\s+\d{4})"
        amount_pattern = r"(?:₹\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"

        date_match = re.match(date_pattern, line)
        if not date_match:
            return None

        date = self._parse_date(date_match.group(1))
        if date is None:
            return None

        # Remove date from line to get description + amount
        rest = line[date_match.end():].strip()
        amount_matches = re.findall(amount_pattern, rest)
        if not amount_matches:
            return None

        # Last number is usually the amount
        amount_str = amount_matches[-1].replace(",", "")
        try:
            amount = float(amount_str)
        except ValueError:
            return None

        # Description is everything before the last amount
        description = re.sub(amount_pattern + r"\s*$", "", rest).strip()
        if not description:
            return None

        merchant = self._clean_merchant(description)
        category = self._categorise(description)

        return Transaction(
            date=date,
            description=description,
            amount=amount,
            category=category,
            merchant_name=merchant,
            transaction_id=str(uuid4()),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date strings — DD/MM/YYYY, DD-MM-YYYY, DD MMM YYYY, etc."""
        date_str = date_str.strip()
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d %b %Y",
            "%d %B %Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%Y-%m-%d",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _categorise(self, description: str) -> str:
        """Assign a category based on keyword matching."""
        desc_lower = description.lower()
        for keyword, category in CATEGORY_KEYWORDS.items():
            if keyword in desc_lower:
                return category
        return "other"

    def _clean_merchant(self, description: str) -> str:
        """
        Clean a raw transaction description into a merchant name.
        Remove UPI IDs, bank refs, timestamps, excess whitespace.
        """
        cleaned = description

        # Remove UPI transaction IDs (e.g., 123456789012@upi)
        cleaned = re.sub(r"\d{8,}@\w+", "", cleaned)
        # Remove generic UPI refs (e.g., UPI/123456/...)
        cleaned = re.sub(r"UPI/\S+", "", cleaned, flags=re.IGNORECASE)
        # Remove bank reference numbers (e.g., REF: 123456789)
        cleaned = re.sub(r"REF\s*:?\s*\d+", "", cleaned, flags=re.IGNORECASE)
        # Remove NEFT/RTGS/IMPS prefixes with reference
        cleaned = re.sub(r"(NEFT|RTGS|IMPS)[/\-]\S+", "", cleaned, flags=re.IGNORECASE)
        # Remove timestamps (e.g., 14:30:22)
        cleaned = re.sub(r"\d{1,2}:\d{2}(:\d{2})?", "", cleaned)
        # Remove date patterns embedded in description
        cleaned = re.sub(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}", "", cleaned)
        # Remove long numeric sequences (transaction IDs)
        cleaned = re.sub(r"\b\d{8,}\b", "", cleaned)
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Remove trailing/leading special chars
        cleaned = re.sub(r"^[\-/\s*]+|[\-/\s*]+$", "", cleaned)

        return cleaned if cleaned else description.strip()

    def _batch_categorise_with_llm(self, transactions: list[Transaction], api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> list[Transaction]:
        """Categorize a list of transactions in batches using the LLM."""
        try:
            from agents.utils import get_llm
            from langchain_core.messages import SystemMessage, HumanMessage
            import json

            llm = get_llm(api_key=api_key, provider=provider, model_id=model_id)
            valid_categories = list(set(CATEGORY_KEYWORDS.values())) + ["other", "rent_maintenance", "education", "cash_withdrawal"]
            
            system = (
                "You are a financial analyst. Categorize the following transactions based on their description. "
                f"Choose ONLY from these categories: {', '.join(valid_categories)}. "
                "Return a JSON list of objects with 'id' and 'category'. Return ONLY valid JSON."
            )
            
            # Process in chunks of 50 to avoid token limits
            refined_txns = []
            for i in range(0, len(transactions), 50):
                batch = transactions[i:i+50]
                tx_list = "\n".join([f"ID: {t.transaction_id} | Desc: {t.description}" for t in batch])
                
                response = llm.invoke([SystemMessage(content=system), HumanMessage(content=tx_list)])
                text = response.content.strip()
                
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                results = json.loads(text)
                for res in results:
                    # Find original txn and update
                    matching = next((t for t in batch if t.transaction_id == res["id"]), None)
                    if matching:
                        matching.category = res["category"]
                        refined_txns.append(matching)
            
            return refined_txns
        except Exception as e:
            logger.error(f"[Parser] Batch categorization failed: {e}")
            return transactions
