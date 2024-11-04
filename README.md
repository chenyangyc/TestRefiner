# TestRefiner

Welcome to the homepage of TestRefiner! This the implementation of our research "Enhancing Test Semantic Clarity for Better LLM-based Unit Test Generation".

## Introduction

TestRefiner is a novel refinement technique that enhances the quality of unit test examples by splitting a complex test into a group of purified ones and improving their textual clarity through a combination of LLMs and program analysis. We first design a test purification component in TestRefiner to simplify complex unit tests, yielding a set of purified tests. We then improve the textual clarity of these purified tests using a program-analysis-enhanced method. This method combines program analysis with the LLMs’ exceptional code comprehension capability, adding essential comments and generating more appropriate identifiers. By doing so, we minimize the influence of LLMs’ hallucinations. Figure 1 shows an overview of TestRefiner.

![Overview of TestRefiner](/Users/yangchen/Library/Application%20Support/typora-user-images/image-20241104231907590.png)

<p align="center">Figure 1: Overview of TestRefiner</p>

## Structure

```
TestRefiner
│
├── code_parser // Static analysis scripts
│
├── core // Definitions of the objects, such as used LLM, unit test, etc.
│
├── data // Experimental data and configuration files
│
├── scripts // Some utility scripts
│
├── vllm_reference: // Scripts used for invoking LLMs used in RQ2
│
├── split_assertion.py // Main code for test purification
│
├── run_llm_refine.py // Main code for refining textual clarity
```

## Setup

1. To fully run our evaluation, please first follow the setups from Defects4J benchmark, and make sure it works fine.
2. Download Junit 4, Mockito 5, powermock 2, hamcreset 2.1, and put it into `/path/to/defects4j/framework/projects/lib` to make sure that the unit tests can compile under junit4. In the future, we will publish a docker image that contains complete runtime environment.
3. Checkout  the defects4j projects used in experiments. Please make sure the structure is `{Bug_id}/fixed` and `{Bug_id}/buggy` for the fixed version and buggy version respectively. 
4. Please follow the `requirements.txt` file for python package installation.



## Execution Instructions

### Data Preparation

Download the focal methods and corresponding unit test information collected from the d4j project from [anonymous_link]( https://drive.google.com/file/d/1PIvw_DueFHlaMwZEkfcoHG8Onhf-HMUh/view?usp=sharing) and place them in the `data` directory.

### Test Purification

Run `split_assertion.py` to purify the tests. The purified test data will be saved in `split_d4j_tests_filtered.json` within the `data` directory.

```shell
python split_assertion.py
```

### Execute Original Unit Tests

Run `setup_base_function.py` to execute the original unit tests and collect relevant information (such as coverage). Results will be stored in `d4j_base_function_{date}` within the `data` directory, where `{date}` represents the execution date.

```shell
python setup_base_function.py
```

### Textual Clarity Refinement

Execute `run_llm_refine.py` to enhance the textual clarity of tests using DeepSeek-V2.5. Before running, ensure that the API key is added in Line 25 of the script:

```python
24 client = OpenAI(
25     api_key="",
26     base_url="https://api.deepseek.com",    
27 )
```

```shell
python run_llm_refine.py
```

The results will be stored in `d4j_llm_refine_{date}` within the `data` directory, with `{date}` indicating the experiment date.

### Execute Refined Unit Tests

Run `run_setup_refine_function.py` to execute the refined unit tests and collect their information (such as coverage). Results will be saved in `d4j_refine_function_{date}` in the `data` directory, where `{date}` represents the execution date.

```shell
python run_setup_refine_function.py
```

### Prompt-Based Test Generation

First, generate prompts for each focal method using `run_rag_gen_prompt_base.py`. Then, use the constructed prompts to guide LLM-based test generation with `vllm_reference`. Finally, execute the newly generated tests to gather results.

```shell
python run_rag_gen_prompt_base.py
cd vllm_reference
python inference_vllm.py
cd ..
python run_setup_rag_function.py
```

Results will be stored in `d4j_rag_function_{date}` within the `data` directory, where `{date}` denotes the execution date.



## Prompt examples

The illustration examples of our examples used in prompts are listed in `./prompt_example`.