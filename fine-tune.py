from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,HfArgumentParser,TrainingArguments,pipeline, logging, Trainer
from peft import LoraConfig, PeftModel, prepare_model_for_kbit_training, get_peft_model
import os,torch, wandb
from datasets import load_dataset
from trl import SFTTrainer
from huggingface_hub import create_repo
from huggingface_hub import HfApi, login

wandb.login(key = '')
run = wandb.init(
    project='Fine tuning mistral 7B',
    job_type="training",
    id="8lyn26du",
)

dataset = load_dataset("TienMat999/vn-legal-qa-rag")
train_data = dataset['train']

def format_example(example):
    return {
        "instruction": "Trả lời câu hỏi dựa trên ngữ cảnh sau",
        "input": f"Ngữ cảnh: {example['context']}\n\nCâu hỏi: {example['question']}",
        "output": example['answers']
    }
formatted_dataset = train_data.map(format_example)

base_model = "1TuanPham/T-VisStar-7B-v0.1"

bnb_config = BitsAndBytesConfig(
    load_in_4bit= True,
    bnb_4bit_quant_type= "nf4",
    bnb_4bit_compute_dtype= torch.bfloat16,
    bnb_4bit_use_double_quant= False,
)
model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
)
model.config.use_cache = False
model.config.pretraining_tp = 1
model.gradient_checkpointing_enable()

tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
tokenizer.padding_side = 'right'
tokenizer.pad_token = tokenizer.eos_token
tokenizer.add_eos_token = True
tokenizer.add_bos_token, tokenizer.add_eos_token

model = prepare_model_for_kbit_training(model)
peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.05,
    r=8,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],

)
model = get_peft_model(model, peft_config)

def tokenize_function(example):
    prompt = f"{example['instruction']}\n\n{example['input']}\n\n### Trả lời:\n{example['output']}"
    tokenized = tokenizer(prompt, truncation=True, max_length=1024, padding="max_length")
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

tokenized_dataset = formatted_dataset.map(tokenize_function, remove_columns=formatted_dataset.column_names)

training_arguments = TrainingArguments(
    output_dir="./results",
    num_train_epochs=1,
    per_device_train_batch_size=24,
    gradient_accumulation_steps=2,
    optim="paged_adamw_32bit",
    save_steps=25,
    logging_steps=25,
    learning_rate=2e-4,
    weight_decay=0.001,
    fp16=False,
    bf16=False,
    max_grad_norm=0.3,
    max_steps=-1,
    warmup_ratio=0.03,
    group_by_length=True,
    lr_scheduler_type="constant",
    report_to="wandb"
)

trainer = Trainer(
    model=model,
    args=training_arguments,
    train_dataset=tokenized_dataset,
    tokenizer=tokenizer
)

trainer.train()

login(token="HF_TOKEN")
api = HfApi()
api.create_repo(repo_id="Mistral-7b-HanhChinh", private=True)

model.push_to_hub("Mistral-7b-HanhChinh")
tokenizer.push_to_hub("Mistral-7b-HanhChinh")