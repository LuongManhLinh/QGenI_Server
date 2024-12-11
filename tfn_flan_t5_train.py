from transformers import T5Tokenizer, T5ForConditionalGeneration, Trainer
import pandas as pd
from transformers import TrainingArguments
from datasets import Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import torch


tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")
model.to('cuda')

df = pd.read_csv('data/tfn_train.csv')
train_df, val_df = train_test_split(df, test_size=0.2, random_state=42)

def get_prompt(passage, statement):
    return f"""Passage:
{passage}
Statement: 
{statement}

Q: 
If the statement is not relevant to the passage, say 'Not Given'.
Otherwise, if the statement is true to the passage, say 'True', and if the statement is false to the passage, say 'False'.
"""

def number_to_label(label_num):
    if label_num == 1:
        return "True"
    elif label_num == 2:
        return "False"
    else:
        return "Not Given"
    

def label_to_number(label):
    if label == "True":
        return 1
    elif label == "False":
        return 2
    else:
        return 3
    

def tokenize_function(examples):
    prompt = get_prompt(examples['Passage'], examples['Statement'])

    label = number_to_label(examples['Type'])

    model_inputs = tokenizer(prompt, max_length=512, truncation=True, padding="max_length")
    labels = tokenizer(label, max_length=512, truncation=True, padding="max_length")

    # Replace padding token id's of the labels by -100 so they are ignored by the loss function
    labels["input_ids"] = [-100 if token == tokenizer.pad_token_id else token for token in labels["input_ids"]]

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

train_set = Dataset.from_pandas(train_df).map(tokenize_function, batched=True)
val_set = Dataset.from_pandas(val_df).map(tokenize_function, batched=True)

# Define training arguments
training_args = TrainingArguments(
    output_dir="/kaggle/working/",
    eval_strategy="epoch",
    learning_rate=1e-5,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_dir="/kaggle/working/",
    report_to="tensorboard",
)

# Initialize Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_set,
    eval_dataset=val_set,
)

# Train the model
trainer.train()

test_df = pd.read_csv('data/tfn_test.csv')
model.eval()
predictions = []

with torch.no_grad():
    for i, row in test_df.iterrows():
        prompt = get_prompt(row['Passage'], row['Statement'])
        input_ids = tokenizer(prompt, max_length=512, truncation=True, return_tensors='pt').input_ids.to('cuda')
        outputs = model.generate(input_ids)
        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)
        predictions.append(label_to_number(prediction.strip()))

accuracy = accuracy_score(test_df['Type'], predictions)

print(f"Accuracy: {accuracy}")

