

import pickle


def read_pkl(pkl_path):
    with open(pkl_path, 'rb') as fr:
        datas = pickle.load(fr)
    return datas


if __name__ == '__main__':
    pkl_path = '/test_refine/data/d4j_rag_gen_prompt_2024-09-05-code_llama/test_append_Formatter.pkl'
    data = read_pkl(pkl_path)
    pass