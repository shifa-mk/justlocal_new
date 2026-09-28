import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("VERYFI_CLIENT_ID")
USERNAME = os.getenv("VERYFI_USERNAME")
API_KEY = os.getenv("VERYFI_API_KEY")

IMAGE_PATH = r"C:\Users\Admin\Desktop\prescription.jpeg"

BASE_URL = "https://api.veryfi.com/api/v8/partner/any-documents"

HEADERS = {
    "CLIENT-ID": CLIENT_ID,
    "AUTHORIZATION": f"apikey {USERNAME}:{API_KEY}",
}

# ---------------------------------------------------------
# STEP 1: Upload prescription to Veryfi
# ---------------------------------------------------------

print("=" * 60)
print("STEP 1: Uploading prescription to Veryfi...")
print("=" * 60)

try:
    with open(IMAGE_PATH, "rb") as file:

        files = {
            "file": (
                "prescription.jpeg",
                file,
                "image/jpeg"
            )
        }

        data = {
            "blueprint_name": "prescription_medication_label"
        }

        response = requests.post(
            BASE_URL,
            headers=HEADERS,
            files=files,
            data=data,
            timeout=120
        )

except FileNotFoundError:
    print("\nERROR: Prescription image not found.")
    print(IMAGE_PATH)
    raise SystemExit

except Exception as e:
    print("\nERROR while uploading:")
    print(e)
    raise SystemExit


print("\nUpload HTTP Status:", response.status_code)

if response.status_code not in [200, 201]:
    print("\nVeryfi returned an error:")
    print(response.text)
    raise SystemExit


try:
    upload_result = response.json()
except Exception:
    print("\nCould not decode Veryfi response:")
    print(response.text)
    raise SystemExit


# Save original upload response
with open(
    "veryfi_upload_response.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        upload_result,
        f,
        indent=2,
        ensure_ascii=False
    )


print("\nUpload response saved to:")
print("veryfi_upload_response.json")


# ---------------------------------------------------------
# STEP 2: Find document ID
# ---------------------------------------------------------

document_id = upload_result.get("id")

if not document_id:
    print("\nCould not find document ID in Veryfi response.")
    print("\nFull response:")
    print(json.dumps(upload_result, indent=2, ensure_ascii=False))
    raise SystemExit


print("\nDocument ID:")
print(document_id)


# ---------------------------------------------------------
# STEP 3: Retrieve processed document
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("STEP 2: Retrieving detailed Veryfi result...")
print("=" * 60)

GET_URL = f"{BASE_URL}/{document_id}"

params = {
    "confidence_details": "true",
    "bounding_boxes": "true"
}

try:
    detail_response = requests.get(
        GET_URL,
        headers=HEADERS,
        params=params,
        timeout=120
    )

except Exception as e:
    print("\nERROR while retrieving document:")
    print(e)
    raise SystemExit


print("\nDetailed response HTTP Status:", detail_response.status_code)

if detail_response.status_code != 200:
    print("\nVeryfi returned an error:")
    print(detail_response.text)
    raise SystemExit


try:
    detailed_result = detail_response.json()
except Exception:
    print("\nCould not decode detailed response:")
    print(detail_response.text)
    raise SystemExit


# ---------------------------------------------------------
# STEP 4: Save COMPLETE response
# ---------------------------------------------------------

with open(
    "veryfi_detailed_response.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        detailed_result,
        f,
        indent=2,
        ensure_ascii=False
    )


print("\nComplete detailed response saved to:")
print("veryfi_detailed_response.json")


# ---------------------------------------------------------
# STEP 5: Print important fields
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("EXTRACTED INFORMATION")
print("=" * 60)

fields_to_show = [
    "id",
    "blueprint_name",
    "template_name",
    "consumer_name",
    "date",
    "expiration_date",
    "instructions",
    "medicine_name",
    "quantity",
    "rx_number",
    "ocr_score",
    "text",
    "handwriting",
    "barcodes",
]


for field in fields_to_show:

    print(f"\n--- {field} ---")

    if field in detailed_result:
        value = detailed_result[field]

        if isinstance(value, (dict, list)):
            print(
                json.dumps(
                    value,
                    indent=2,
                    ensure_ascii=False
                )
            )
        else:
            print(value)

    else:
        print("NOT PRESENT")


# ---------------------------------------------------------
# STEP 6: Print all top-level keys
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("ALL TOP-LEVEL RESPONSE FIELDS")
print("=" * 60)

for key in detailed_result.keys():
    print(key)


print("\n" + "=" * 60)
print("DONE")
print("=" * 60)