import sys
sys.path.insert(0, '.')
from data_loader import load_project, project_to_text
from rag_engine import compute_rule_based_rag

files = ['data/Project Plan B.xlsx', 'data/S2P Project.xlsx']
for fname in files:
    print(f'\n==== {fname} ====')
    proj = load_project(fname)
    print('Project:', proj['project_name'])
    print('Manager:', proj['project_manager'])
    print('Summary:', proj['summary'])
    score = compute_rule_based_rag(proj)
    print('Rule-based RAG:', score['overall_rag'])
    for k, v in score['dimensions'].items():
        print(f'  {k}: {v["rag"]} - {v["detail"]}')
    text = project_to_text(proj)
    print('\n--- Project text (first 600 chars) ---')
    print(text[:600])
