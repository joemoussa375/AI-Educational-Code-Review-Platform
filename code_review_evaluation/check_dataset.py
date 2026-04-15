import json
d = json.load(open('testing/dataset.json', encoding='utf-8'))
t1 = sum(1 for e in d if e['tier']==1)
t2 = sum(1 for e in d if e['tier']==2)
t3 = sum(1 for e in d if e['tier']==3)
print(f'Total={len(d)} | T1={t1} T2={t2} T3={t3}')
ids = sorted(e['id'] for e in d)
print('All IDs:', ids)
missing = [i for i in range(1,101) if i not in ids]
print('Missing:', missing)
