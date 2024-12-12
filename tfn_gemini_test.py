from api import GeminiAPI
import pandas as pd
from sklearn.metrics import accuracy_score
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

df = pd.read_csv('data/tfn_train.csv')
predicts = []
values = []
for i in range(1, 100):
    try:
        prompt = get_prompt(df['Passage'][i], df['Statement'][i])
        pred = GeminiAPI.generate_content(prompt)
        if pred.startswith("True"):
            predicts.append(1)
        elif pred.startswith("False"):
            predicts.append(2)
        else:
            predicts.append(3)
        print(i)
        values.append(df['Type'][i])
        time.sleep(1)
    except:
        break

print(accuracy_score(values, predicts))
