import os
import json
import random


def corpus_builder(file_paths):
    duplicate_count = 0
    corpus_dict = {
        "sources": [],
        "data": []
    }
    
    for file_path in file_paths:
        with open(os.path.join("..", "Data", file_path), 'r', encoding='utf-8') as file:
            file_data = json.load(file)

            if file_data:
                corpus_dict['sources'].append(file_data['metadata']['source'])

            for entry in file_data['data']:
                if entry not in corpus_dict['data']:
                    corpus_dict['data'].append(entry)
                else:
                    duplicate_count += 1
    
    random.shuffle(corpus_dict['data'])

    output_file = os.path.join("..", "Data", "corpus.json")
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(corpus_dict, file, ensure_ascii=False, indent=4)

    print(f"\nCorpus built with {duplicate_count} duplicates removed")
    print(f"Corpus contains {len(corpus_dict['data'])} entries")

data_dir = os.path.join("..", "Data")
corpus_file_paths = [file for file in os.listdir(data_dir) if file not in ["corpus.json", "corpus_initial.csv", "corpus_test.csv", "corpus_train.csv"]]

if corpus_file_paths:
    print("\nBuilding corpus from the following files:\n", corpus_file_paths)
    corpus_builder(corpus_file_paths)