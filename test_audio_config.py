from google.genai import types
print(dir(types))
# Try to find modalities
for attr in dir(types):
    if "Modality" in attr or "MODALITY" in attr or "modalities" in attr.lower():
        print("Found:", attr)
