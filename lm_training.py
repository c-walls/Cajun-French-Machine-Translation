import json
import torch
import numpy as np
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, get_linear_schedule_with_warmup


def load_model(base_model, legacy=False):
    tokens_to_add = ['<|Eng|>', '<|CajFr|>']
    tokenizer = AutoTokenizer.from_pretrained(base_model, clean_up_tokenization_spaces=True, legacy=legacy, additional_special_tokens=tokens_to_add)
    model = AutoModelForSeq2SeqLM.from_pretrained(base_model)
    model.cuda()

    return tokenizer, model


def format_translation_data(data, tokenizer, max_seq_len=128):
    # Randomly select input and target languages
    input_lang, target_lang = np.random.choice(['English', 'Cajun French'], size=2, replace=False)

    # Get the parallel senteces from the data
    input_text = data[input_lang]
    target_text = data[target_lang]
    target_lang_token = '<|Eng|>' if target_lang == 'English' else '<|CajFr|>'

    # Tokenize the input and target text
    input_ids = tokenizer.encode(
        text = target_lang_token + input_text,
        return_tensors = 'pt',
        padding = 'max_length',
        truncation = True,
        max_length = max_seq_len
    )
  
    target_ids = tokenizer.encode(
        text = target_text,
        return_tensors = 'pt',
        padding = 'max_length',
        truncation = True,
        max_length = max_seq_len
    )

    return input_ids, target_ids


def transform_batch(batch, tokenizer):
    inputs = []
    targets = []

    # Set the max sequence length for the batch
    longest_seq = max([max(len(sentence['English']), len(sentence['Cajun French'])) for sentence in batch])
    max_seq_len = min(128, longest_seq + 4)

    # Tokenize and separate the input and target texts
    for sentence_pair in batch:
        input_ids, target_ids = format_translation_data(sentence_pair, tokenizer, max_seq_len)
        inputs.append(input_ids)
        targets.append(target_ids)
    
    # Format as torch tensors
    batch_input_ids = torch.cat(inputs).cuda()
    batch_target_ids = torch.cat(targets).cuda()

    return batch_input_ids, batch_target_ids


def data_generator(dataset, tokenizer, batch_size=32):
    np.random.shuffle(dataset)

    # Generate batches of data
    for i in range(0, len(dataset), batch_size):
        raw_batch = dataset[i:i+batch_size]
        batch_data = transform_batch(raw_batch, tokenizer)

        yield batch_data


def eval_model(model, tokenizer, test_data, batch_size):
    model.eval()
    eval_generator = data_generator(test_data, tokenizer, batch_size)

    with torch.no_grad():
        eval_loss = []
        for batch in eval_generator:
            input_ids, target_ids = batch
            loss = model(input_ids, labels=target_ids).loss
            eval_loss.append(loss.item())

    return np.mean(eval_loss)


with open('Data/corpus.json', 'r', encoding='utf-8') as file:
    corpus_data = json.load(file)['data']

testing_data = corpus_data[:1000]
training_data = corpus_data[1000:]
mt5_tokenizer, mt5_model = load_model('google/mt5-small', True)


epochs = 1
batch_size = 6
learning_rate = 5e-4
n_batches = len(corpus_data) // batch_size

total_steps = epochs * n_batches
warmup_steps = int(0.1 * total_steps)
optimizer = torch.optim.AdamW(mt5_model.parameters(), lr=learning_rate)
scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

train_loss = []
eval_loss = []
for epoch_idx in range(epochs):
    train_generator = data_generator(training_data, mt5_tokenizer, batch_size=batch_size)

    # Training loop
    for batch_idx, batch in tqdm(enumerate(train_generator), total=n_batches):
        input_ids, target_ids = batch

        mt5_model.train()
        optimizer.zero_grad()

        loss = mt5_model(input_ids, labels=target_ids).loss
        train_loss.append(loss.item())
        loss.backward()

        optimizer.step()
        scheduler.step()

        if batch_idx % 100 == 0:
            print(f'Epoch: {epoch_idx},  Avg Loss: {np.mean(train_loss[-100:]):.3f},  Learning Rate: {scheduler.get_last_lr()[0]:.6f}')

    # Evaluate progress on the test set
    test_loss = eval_model(mt5_model, mt5_tokenizer, testing_data, batch_size)
    eval_loss.append(test_loss)
    print(f'Epoch: {epoch_idx},  Test Loss: {test_loss:.3f}')

# Save the model
torch.save(mt5_model.state_dict(), 'mt5_small_model1.pt')

import numpy as np
np.save('train_loss.npy', train_loss)
np.save('test_loss.npy', eval_loss)