import json
import re


INPUT_FILE = "veryfi_detailed_response.json"
OUTPUT_FILE = "parsed_prescription.json"


def get_value(data, field):
    """
    Veryfi sometimes returns fields like:
    {"value": "SHIFA MOHAMMAD"}

    Extract the actual value.
    """
    value = data.get(field)

    if isinstance(value, dict):
        return value.get("value")

    return value
def extract_symptoms(text):
    """
    Extract symptoms from OCR text.

    Handles common OCR errors found in prescription handwriting,
    while avoiding diagnosis or unsupported symptom inference.
    """

    symptoms = []

    if not text:
        return symptoms

    # -----------------------------------------------------
    # Normalize OCR text
    # -----------------------------------------------------

    normalized_text = str(text)

    # Normalize whitespace
    normalized_text = re.sub(
        r"\s+",
        " ",
        normalized_text
    ).strip()

    # Common OCR corrections observed in this prescription.
    # "Atools" is an OCR corruption of "stools".
    normalized_text = re.sub(
        r"\bAtools\b",
        "stools",
        normalized_text,
        flags=re.IGNORECASE
    )

    # OCR sometimes reads handwritten "1 day" as "I say".
    normalized_text = re.sub(
        r"\bI\s+say\b",
        "1 day",
        normalized_text,
        flags=re.IGNORECASE
    )

    # -----------------------------------------------------
    # Helper
    # -----------------------------------------------------

    def add_symptom(name, duration=None, present=True):

        # Avoid duplicate positive symptoms
        if present:
            for existing in symptoms:
                if (
                    existing.get("name", "").lower()
                    == name.lower()
                    and existing.get("present", True)
                ):
                    return

        symptom = {
            "name": name
        }

        if duration:
            symptom["duration"] = duration

        if not present:
            symptom["present"] = False

        symptoms.append(symptom)

    # -----------------------------------------------------
    # Vomiting
    # -----------------------------------------------------

    vomiting = re.search(
        r"\bvomit(?:ing)?\b"
        r".{0,30}?"
        r"(\d+)\s*(?:day|days|d)\b",
        normalized_text,
        re.IGNORECASE
    )

    if vomiting:

        number = int(vomiting.group(1))

        duration = (
            "1 day"
            if number == 1
            else f"{number} days"
        )

        add_symptom(
            "Vomiting",
            duration
        )

    # -----------------------------------------------------
    # Loose stools
    # -----------------------------------------------------

    loose_stools = re.search(
        r"\b"
        r"(?:"
        r"loose\s+stools?"
        r"|loose\s+motions?"
        r"|diarrhea"
        r"|diarrhoea"
        r")"
        r"\b"
        r".{0,30}?"
        r"(\d+)\s*(?:day|days|d)\b",
        normalized_text,
        re.IGNORECASE
    )

    if loose_stools:

        number = int(loose_stools.group(1))

        duration = (
            "1 day"
            if number == 1
            else f"{number} days"
        )

        add_symptom(
            "Loose stools",
            duration
        )

    # -----------------------------------------------------
    # No fever / negative fever
    # -----------------------------------------------------

    no_fever = re.search(
        r"\b"
        r"(?:no|denies|without)"
        r"\s+"
        r"(?:"
        r"h/?o\s*"
        r"|history\s+of\s*"
        r"|do\s+"
        r")?"
        r"fever"
        r"\b",
        normalized_text,
        re.IGNORECASE
    )

    if no_fever:

        add_symptom(
            "Fever",
            present=False
        )

    else:

        # Only mark fever present when explicitly mentioned.
        fever = re.search(
            r"\bfever\b",
            normalized_text,
            re.IGNORECASE
        )

        if fever:
            add_symptom("Fever")

    return symptoms
def extract_medicines(text, structured_medicine):
    """
    Extract medicine information from Veryfi OCR text.

    We intentionally avoid guessing unclear dosage/frequency.
    """

    medicines = []

    # -----------------------------------------------------
    # Dibact DS
    # -----------------------------------------------------

    if re.search(r"Dibact\s*DS", text, re.IGNORECASE):

        duration = None

        # OCR clearly contains "5 Day" near Dibact DS
        dibact_match = re.search(
            r"Dibact\s*DS.*?5\s*Day",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if dibact_match:
            duration = "5 days"

        medicines.append({
            "name": "Dibact DS",
            "strength": None,
            "dosage": None,
            "frequency": None,
            "duration": duration,
            "confidence": "partial"
        })

    # -----------------------------------------------------
    # Emset
    # -----------------------------------------------------

    emset_match = re.search(
        r"Emset\s+(\d+)\s*mg\s+([A-Za-z]+)",
        text,
        re.IGNORECASE
    )

    if emset_match:

        strength = f"{emset_match.group(1)} mg"
        instruction = emset_match.group(2).upper()

        frequency = None

        if instruction == "SOS":
            frequency = "SOS"

        medicines.append({
            "name": "Emset",
            "strength": strength,
            "dosage": None,
            "frequency": frequency,
            "duration": None,
            "confidence": "partial"
        })

    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    if not medicines and structured_medicine:

        # Veryfi may return multiple medicines separated by ;
        names = re.split(r"\s*;\s*", structured_medicine)

        for name in names:

            name = name.strip()

            if not name:
                continue

            medicines.append({
                "name": name,
                "strength": None,
                "dosage": None,
                "frequency": None,
                "duration": None,
                "confidence": "low"
            })

    return medicines


def main():

    print("=" * 60)
    print("PRESCRIPTION PARSER")
    print("=" * 60)

    # -----------------------------------------------------
    # Load Veryfi response
    # -----------------------------------------------------

    try:
        with open(
            INPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

    except FileNotFoundError:

        print("\nERROR:")
        print(f"{INPUT_FILE} not found.")

        print("\nRun veryfi_test.py first.")

        return

    # -----------------------------------------------------
    # Basic prescription information
    # -----------------------------------------------------

    patient_name = get_value(
        data,
        "consumer_name"
    )

    prescription_date = get_value(
        data,
        "date"
    )

    structured_medicine = get_value(
        data,
        "medicine_name"
    )

    raw_text = data.get(
        "text",
        ""
    )

    # -----------------------------------------------------
    # Extract symptoms
    # -----------------------------------------------------

    symptoms = extract_symptoms(
        raw_text
    )

    # -----------------------------------------------------
    # Extract medicines
    # -----------------------------------------------------

    medicines = extract_medicines(
        raw_text,
        structured_medicine
    )

    # -----------------------------------------------------
    # Final structured result
    # -----------------------------------------------------

    result = {

        "success": True,

        "patient": {
            "name": patient_name
        },

        "date": prescription_date,

        "symptoms": symptoms,

        "medicines": medicines,

        "source": {
            "provider": "Veryfi",
            "blueprint": data.get(
                "blueprint_name"
            ),
            "document_id": data.get(
                "id"
            )
        }
    }

    # -----------------------------------------------------
    # Save result
    # -----------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False
        )

    # -----------------------------------------------------
    # Print result
    # -----------------------------------------------------

    print("\nParsed prescription:")
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )

    print("\n" + "=" * 60)
    print("Saved to:")
    print(OUTPUT_FILE)
    print("=" * 60)


if __name__ == "__main__":
    main()