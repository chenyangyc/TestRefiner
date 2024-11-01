import argparse
import os
import numpy as np
import json
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from tqdm import tqdm

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=str,
        default="codex002",
        help="Type of Codex Model to run",
    )
    parser.add_argument(
        "--source_file",
        type=str,
        default="./ds1000_data",
        help="Path to the downloaded DS-1000 data",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature of the Codex sampling distribtuion.",
    )
    parser.add_argument(
        "--top_p",
        type=float,
        default=0.95,
        help="Top-p cutoff of the Codex sampling distribtuion",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=1024,
        help="Number of maximum tokens for Model to generate",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=20,
        help="Number of requests to issue at one time",
    )
    parser.add_argument(
        "--card",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--totalnumber",
        type=int,
        required=True,
    )    
    args = parser.parse_args()
    
    filepath = args.source_file
    dp_size = args.totalnumber
    dp_rank = args.card
    model_path = args.model
    
    lines = open(filepath, "r").readlines()
    data = [json.loads(line) for line in lines]
    
    prompt_indices_split = np.array_split(range(len(data)), dp_size)
    prompt_indices = prompt_indices_split[dp_rank]
    
    available_gpus = os.environ['CUDA_VISIBLE_DEVICES'].split(',')
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    llm = LLM(model=model_path, tensor_parallel_size=len(available_gpus), max_model_len=16384, trust_remote_code=True)
    # llm = LLM(model=model_path, tensor_parallel_size=len(available_gpus), trust_remote_code=True)
    sampling_params = SamplingParams(temperature=args.temperature, max_tokens=4096, stop_token_ids=[tokenizer.eos_token_id], stop=['<|EOT|>'])

    outputfile = open('output'+str(dp_rank)+'.jsonl', 'w')
    
    if args.temperature == 0:
        args.top_p = 1.0
    
    for idx in tqdm(range(0, len(prompt_indices), args.batch_size), desc='Generating for rank '+str(dp_rank)):
        prompts = []
        result = []
        for j in prompt_indices[idx:idx + args.batch_size]:
            prompts.append(data[j]['prompt'])
            result.append(data[j])
        
        outputs = llm.generate(prompts, sampling_params=sampling_params)

        outputs = sorted(outputs, key=lambda x: int(x.request_id)) # sort outputs by request_id

        result_with_prompt = {}
        for output in outputs:
            result_with_prompt[output.prompt] = output.outputs[0].text

        for i in range(len(prompts)):
            if prompts[i] in result_with_prompt:
                result[i]['completion'] = result_with_prompt[prompts[i]]
            else:
                result[i]['completion'] = 'out of max_tokens'
            outputfile.write(json.dumps(result[i])+'\n')
            outputfile.flush()
    outputfile.close()


# CUDA_VISIBLE_DEVICES=0 python run_inference_vllm.py --model /data/public/deepseek-coder-6.7b-instruct --temperature 0.0 --source_file test_prompt.jsonl --top_p 0.95 --batch_size 4 --card 0 --totalnumber 1 --max_tokens 4096