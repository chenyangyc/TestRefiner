import openai

openai.api_key = "EMPTY"
openai.api_base = "http://172.28.102.8:6668/v1"
my_model = "Phind-CodeLlama-34B-v2"

# openai.api_base = "https://api.deepseek.com/v1"
# openai.api_key = "sk-fe4c3f17dfb24913ad5127e37a6acdc6"
# my_model = "deepseek-coder"

class ChatBot:

    def __init__(self, api_base, temperature=0, max_tokens=4096):
        self.history = []
        self.max_context = 10
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = ("You are an intelligent programming assistant to help user writing Java unit tests. "
                              "If you provide code in your response, the code you write should be in format ```java <code> ```")
        openai.api_base = api_base
        self.model = my_model


    def chat(self, prompt, add_to_history=False):
        prompts = [{"role":"system", "content": self.system_prompt}]
        context = ""
        
        # for history in self.history:
        #     context += f"{history['question']}\n{history['answer']}\n"
        #     prompts.append({"role": "user", "content": history['question']})
        #     prompts.append({"role": "assistant", "content": history['answer']})
        
        prompts.append({"role": "user", "content": prompt})
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=prompts,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        res = response.choices[0].message.content
        
        if len(self.history) > self.max_context:
            # self.history.pop(0)
            # delete items from the end of the list
            self.history.pop()
        if add_to_history:
            self.history.append({"question":prompt,"answer":res})
            
        return res


    def chat_cache(self, stage1_prompt, stage1_response=None, stage2_prompt=None):
        prompts = [{"role":"system", "content": self.system_prompt}]

        prompts.append({"role": "user", "content": stage1_prompt})
        if stage1_response:
            prompts.append({"role": "assistant", "content": stage1_response})
        if stage2_prompt:
            prompts.append({"role": "user", "content": stage2_prompt})
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=prompts,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        res = response.choices[0].message.content

        return res


if __name__ == "__main__":
    chatbot = ChatBot("https://api.deepseek.com/v1")
    prompt = 'hi'
    chatbot.chat(prompt, True)
    
    for history in chatbot.history:
        print("Question:")
        print(history["question"])
        print("Answer:")
        print(history["answer"])
    print("----")
