import subprocess


model = '/data/public/CodeLlama-34b-Instruct-hf'
DATADIRs = ["all_rag_gen_base_prompt_2024-09-04-2.jsonl", "all_rag_gen_refine_prompt_2024-09-04-2.jsonl"]
batch_size = 4


# model = "/data/public/deepseek-coder-6.7b-instruct"
# model = '/data/public/CodeLlama-13b-Instruct-hf'
# # DATADIR= "all_rag_gen_base_prompt.jsonl"
# DATADIRs = ["all_rag_gen_refine_prompt_2024-09-06-code_llama_13b.jsonl", "all_rag_gen_base_prompt_2024-09-06-code_llama_13b.jsonl"]
# batch_size = 4

# model = "/data/public/Phind-CodeLlama-34B-v2"
# DATADIRs = ["all_rag_gen_base_prompt_2024-09-06-phind.jsonl", "all_rag_gen_refine_prompt_2024-09-06-phind.jsonl"]
# batch_size = 4

gpus = [0,3]
per_dp_rank_cards = 2
dp_size = len(gpus) // per_dp_rank_cards
print(dp_size)

for DATADIR in DATADIRs:
    processes = []
    for i in range(dp_size):
        cuda_device = ""
        for j in range(per_dp_rank_cards):
            cuda_device += str(gpus[i * per_dp_rank_cards + j]) + ","
        
        cmd = f"CUDA_VISIBLE_DEVICES={cuda_device[:-1]} python run_inference_vllm.py --model {model} --temperature 0.0 --source_file {DATADIR} --top_p 0.95 --batch_size {batch_size} --card {i} --totalnumber {dp_size} --max_tokens 4096"
        print(cmd)
        # exit()
        p = subprocess.Popen(cmd, shell=True)
        processes.append(p)
    # exit()
    for p in processes:
        p.wait()

    model_name = model.split("/")[-1]
    outputfile = model_name + '_' +  DATADIR.replace('prompt', 'output')
    outputfile = open(outputfile, "w")

    for i in range(dp_size):
        filepath = f"output{i}.jsonl"
        lines = open(filepath).readlines()
        for line in lines:
            outputfile.write(line)
        subprocess.Popen(f"rm {filepath}", shell=True)
    outputfile.close()
