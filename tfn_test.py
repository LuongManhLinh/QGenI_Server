from transformers import T5Tokenizer, T5ForConditionalGeneration
import pandas as pd
import time

def get_prompt(passage, statement):
    return f"""Passage:
{passage}
Statement: 
{statement}

Q: 
If the statement is not relevant to the passage, say 'Not Given'.
Otherwise, if the statement is true to the passage, say 'True', and if the statement is false to the passage, say 'False'.
"""


tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
model = T5ForConditionalGeneration.from_pretrained("model/tfn_model").to('cuda')

df = pd.read_csv('data/tfn_test.csv')

start_time = time.time()
prompt = get_prompt(df['Passage'][1], df['Statement'][1])

inputs = tokenizer(prompt, return_tensors="pt").input_ids.to('cuda')
outputs = model.generate(inputs)

print(time.time() - start_time)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))