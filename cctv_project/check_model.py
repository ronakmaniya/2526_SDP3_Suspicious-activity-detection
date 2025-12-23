from transformers import AutoImageProcessor, AutoModelForVideoClassification

model_name = "MCG-NJU/videomae-base"

processor = AutoImageProcessor.from_pretrained(model_name)

model = AutoModelForVideoClassification.from_pretrained(
    model_name,
    num_labels=2,
    ignore_mismatched_sizes=True,  # allows replacing the classification head
)

print(f"Loaded: {model_name}")
print(f"Model class: {model.__class__.__name__}")
print("VideoMAE-Base loaded successfully with 2 classes")
