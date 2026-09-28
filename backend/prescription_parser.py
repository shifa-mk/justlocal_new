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
    Extract simple symptom information from the OCR text.

    We only extract what the OCR actually shows.
    We do not diagnose anything.
    """

    symptoms = []

    # Vomiting
    vomiting = re.search(
        r"Vomiting\s+(\d+)\s*Day",
        text,
        re.IGNORECASE
    )

    if vomiting:
        symptoms.append({
            "name": "Vomiting",
            "duration": f"{vomiting.group(1)} day"
        })

    # Loose stools
    loose_stools = re.search(
        r"Loose\s+(?:Atools|stools).*?(\d+)\s*(?:Day|day)",
        text,
        re.IGNORECASE
    )

    if loose_stools:
        symptoms.append({
            "name": "Loose stools",
            "duration": f"{loose_stools.group(1)} day"
        })

    # No fever
    if re.search(
        r"No\s+(?:do\s+)?fever",
        text,
        re.IGNORECASE
    ):
        symptoms.append({
            "name": "Fever",
            "present": False
        })

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