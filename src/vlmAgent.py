from collections import Counter

import numpy as np
from sympy import im
from src.utils import *
import pdb
import numpy as np
import pdb
import torch
import time
from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration, BitsAndBytesConfig, AutoTokenizer, AutoProcessor, VipLlavaForConditionalGeneration, LlavaForConditionalGeneration
import sentencepiece as spm
import torch.nn as nn
from PIL import Image
from src.utils import *
import io
import os
import google.generativeai as genai

class VLMAgent:
    """
    Trivial agent for testing
    """
    def __init__(self, **kwargs):
        self.name = "not implemented"

    def call(self, visual_prompt: np.array, text_prompt: str):
        return ""
    
    def call_chat(self, history, visual_prompt, text_prompt, add_timesteps_prompt=True, step=None):
        return ""

    def reset(self):
        pass


class LlavaAgent(VLMAgent):

    def __init__(self, **kwargs):
        
        self.setup_kwargs = kwargs
        self.folder = 'llava-hf'
        self.model_cls = LlavaNextForConditionalGeneration
        self.processor_cls = LlavaNextProcessor
        self.is_setup = False
        name = kwargs['name']
        if name == '34b':
            self.name = "llava-v1.6-34b-hf"
        elif name == '13b':
            self.name = "llava-v1.6-vicuna-13b-hf"
        elif name == 'mistral7b':
            self.name="llava-v1.6-mistral-7b-hf"
        elif name == 'vicuna7b':
            self.name="llava-v1.6-vicuna-7b-hf"
        elif name == 'qwen7b':
            self.name='llava-interleave-qwen-7b-hf'
            self.processor_cls = AutoProcessor
            self.model_cls = LlavaForConditionalGeneration
        elif name == 'dpo':
            self.name='llava-interleave-qwen-7b-dpo-hf'
            self.processor_cls = AutoProcessor
            self.model_cls = LlavaForConditionalGeneration         
        elif name == '8b':
            self.name='llama3-llava-next-8b-hf'
        elif name == '72b':
            self.name='llava-next-72b-hf'
        elif name == 'vip7b':
            self.name = 'vip-llava-7b-hf'
            self.processor_cls = AutoProcessor
            self.model_cls = VipLlavaForConditionalGeneration

        elif name == 'vip13b':
            self.folder = 'llava-hf'
            self.name = 'vip-llava-13b-hf'
            self.processor_cls = AutoProcessor
            self.model_cls = VipLlavaForConditionalGeneration
        else:
            raise(f"Name {name} is not a valid llava name")
    def setup(self, name = None, quantize=False, torch_dtype=torch.float16,
               low_cpu_mem_usage=True, device_map=None, use_flash_attention_2=False,
               do_sample=False, num_beams=1
               ):

        model_kwargs = {}
        model_kwargs['do_sample'] = do_sample
        model_kwargs['num_beams'] = num_beams
        model_kwargs['pretrained_model_name_or_path'] = f'{self.folder}/{self.name}'

        if quantize:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
            model_kwargs['quantization_config'] = quantization_config
        if device_map:
            model_kwargs['device_map'] = 'auto'
        model_kwargs['torch_dtype'] = torch_dtype
        model_kwargs['low_cpu_mem_usage'] = low_cpu_mem_usage
        if use_flash_attention_2:
            model_kwargs['attn_implementation'] = 'flash_attention_2'
        # pdb.set_trace()
        self.model = self.model_cls.from_pretrained(**model_kwargs)
        self.processor = self.processor_cls.from_pretrained(f'{self.folder}/{self.name}')
        if not device_map:
            self.model = self.model.to('cuda')
    
    def call_multi_image(self, conversation, images):
        if not self.is_setup:
            self.setup(**self.setup_kwargs)
            self.is_setup=True
        prompt = self.processor.apply_chat_template(conversation, add_generation_prompt=True)
        ims = []
        for image in images:
            ims.append(Image.fromarray(image[:, :, 0:3]))
        print(prompt)
        inputs = self.processor(prompt, images=ims, return_tensors="pt").to(self.model.device, self.model.dtype)
        t = time.time()
        input_tokens = inputs['input_ids'].shape[1]
        output = self.model.generate(**inputs, max_new_tokens=600)
        duration = time.time() - t
        tokens_generated = output.shape[1]-input_tokens
        print(f'{self.name} finished inference, took {duration} seconds, speed of {tokens_generated/duration} t/s')

        output_text = self.processor.decode(output[0][input_tokens:], skip_special_tokens=True)
        
        return output_text, {'tokens_generated': tokens_generated, 'duration': duration, 'input_tokens': input_tokens}


    def call(self, visual_prompt: np.array, text_prompt: str, num_samples=0):
        
        if not self.is_setup:
            self.setup(**self.setup_kwargs)
            self.is_setup=True

        conversation = [
            {
            "role": "user",
            "content": [
                {"type": "text", "text": text_prompt},
                {"type": "image"},
                ],
            },
        ]
        prompt = self.processor.apply_chat_template(conversation, add_generation_prompt=True)


        if visual_prompt.shape[-1] == 4:
            visual_prompt = visual_prompt[:, :, 0:3]
        image = Image.fromarray(visual_prompt, mode='RGB') 

        inputs = self.processor(prompt, image, return_tensors="pt").to(self.model.device, self.model.dtype)
        t = time.time()
        input_tokens = inputs['input_ids'].shape[1]
        output = self.model.generate(**inputs, max_new_tokens=600)
        duration = time.time() - t
        tokens_generated = output.shape[1]-input_tokens
        print(f'{self.name} finished inference, took {duration} seconds, speed of {tokens_generated/duration} t/s')

        output_text = self.processor.decode(output[0][input_tokens:], skip_special_tokens=True)
        
        return output_text, {'tokens_generated': tokens_generated, 'duration': duration, 'input_tokens': input_tokens}

class GeminiAgent(VLMAgent):
    
    def __init__(self, model="gemini-1.5-flash", sys_instruction=None):
        self.name = model
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])

        # Create the model
        self.generation_config = {
        "temperature": 1,
        "top_p": 0.8,
        "top_k": 64,
        "max_output_tokens": 500,
        "response_mime_type": "text/plain",
        }

        self.model = genai.GenerativeModel(
        model_name = model,
        generation_config=self.generation_config,
        system_instruction=sys_instruction
        )
        self.session = self.model.start_chat(history=[])

    def call_chat(self, history, images, text_prompt, add_timesteps_prompt=True, step=None):
        
  
        try:
            t = time.time()
            #images = [genai.upload_file(im.tobytes()) for im in images]
            response = self.session.send_message([text_prompt] + images)
            if len(self.session.history) > 2*history:
                self.session.history = self.session.history[-2*history:]
            if add_timesteps_prompt:
                self.session.history[-2].parts[0].text = f"[PREVIOUS OBSERVATION] Timestep {step}:"
            else:
                self.session.history[-2].parts = self.session.history[-2].parts[1:]
                # response = chat_session.send_message("INSERT_INPUT_HERE")
            # response = self.model.generate_content([image, text_prompt])
            finish = time.time() - t
            time.sleep(max(0.01, 3.5 - finish))
            resp = response.text
            perf = {'tokens_generated': response.usage_metadata.candidates_token_count, 'duration': finish, 'input_tokens': response.usage_metadata.prompt_token_count}
            print(f'\n{self.name} finished inference, took {finish} seconds, speed of {perf["tokens_generated"]/finish} t/s')
        
        except Exception as e:  
            resp = f"ERROR: {e}"
            print(resp)
            perf = {'tokens_generated': 0, 'duration': 1, 'input_tokens': 0}

        # history.append(            {
        #     "role": "model",
        #     "parts": [
        #         response.text
        #     ],
        # },)

        return resp, perf
    
    def reset(self):
        del self.session
        self.session = self.model.start_chat(history=[])

    def call(self, visual_prompt: np.array, text_prompt: str, num_samples=None):

        if visual_prompt.shape[-1] == 4:
            visual_prompt = visual_prompt[:, :, 0:3]
        image = Image.fromarray(visual_prompt, mode='RGB') 

        t = time.time()
        response = self.model.generate_content([image, text_prompt])
        finish = time.time() - t
        time.sleep(max(0.01, 3.5 - finish))
        perf = {'tokens_generated': response.usage_metadata.candidates_token_count, 'duration': finish, 'input_tokens': response.usage_metadata.prompt_token_count}
        print(f'{self.name} finished inference, took {finish} seconds, speed of {perf["tokens_generated"]/finish} t/s')

        
        return response.text, perf