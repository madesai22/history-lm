import file_handeling as fh
import re
import random
import pandas as pd
import json
import codecs
import wiki_functions as wf 
import os
from transformers import set_seed
from transformers import pipeline, set_seed
from transformers import T5Tokenizer, T5ForConditionalGeneration
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from transformers import AutoTokenizer, FalconForCausalLM
import pandas as pd
import datetime
from numba import jit, cuda

def initiate_falcon(fourtyb=False):
    if fourtyb:
        tokenizer = AutoTokenizer.from_pretrained("tiiuae/falcon-40b")
        model = FalconForCausalLM.from_pretrained("tiiuae/falcon-40b",device_map = "auto")
        model_string = "falcon40b"

    tokenizer = AutoTokenizer.from_pretrained("tiiuae/falcon-7b")
    model = FalconForCausalLM.from_pretrained("tiiuae/falcon-7b",device_map = "auto")
    model_string = "falcon7b"
    return model, tokenizer, model_string

def initiate_falcon_instruct():
    tokenizer = AutoTokenizer.from_pretrained("tiiuae/falcon-7b-instruct")
    model = FalconForCausalLM.from_pretrained("tiiuae/falcon-7b-instruct",device_map = "auto")
    model_string = "falcon7b-instruct"
    return model, tokenizer, model_string

def falcon_text_to_text(prompt, model,tokenizer):
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to("cuda")
    outputs = model.generate(input_ids)
    return(tokenizer.decode(outputs[0]))

def initiate_flan5_text_to_text(xxl = False):
    if xxl: 
         tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-xxl")
         model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-xxl", device_map="auto")
         model_string = "flant5xxl"
    else:
         tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
         model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base", device_map="auto") 
         model_string = "flant5base"
    return model, tokenizer, model_string

def flant5_text_to_text(prompt, model,tokenizer):
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to("cuda")
    outputs = model.generate(input_ids)
    return(tokenizer.decode(outputs[0]))

def initiate_gpt2(medium = False, large = False):
    if medium: 
        model = GPT2LMHeadModel.from_pretrained("gpt2-medium",device_map="auto")
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2-medium")
        model_string = "gpt2medium"
    elif large:
        model = GPT2LMHeadModel.from_pretrained("gpt2-large",device_map="auto")
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2-large")
        model_string = "gpt2large"
    else:
       tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
       model = GPT2LMHeadModel.from_pretrained("gpt2",device_map="auto")  
       model_string = "gpt2"  
    return model, tokenizer, model_string

def gpt2_text_to_text(prompt, model, tokenizer, contrastive=True):
    input_ids = tokenizer(prompt, return_tensors='pt').input_ids.to("cuda")
   # outputs = model.generate(input_ids, pad_token_id=tokenizer.eos_token_id, max_new_tokens=200, do_sample = True) # do_sample = True, top_k=50)
    # contrastive search
    if contrastive:
        outputs = model.generate(input_ids, pad_token_id=tokenizer.eos_token_id, penalty_alpha=0.6, top_k=4, max_new_tokens=3)
    else:
        outputs = model.generate(input_ids, pad_token_id=tokenizer.eos_token_id, do_sample=True, top_k=0, temperature = 0.6, max_new_tokens=2)

    return (tokenizer.decode(outputs[0], skip_special_tokens=True))


def gpt_2_generate(prompt):
    generator = pipeline('text-generation', model='gpt2')
    response = generator(prompt, max_new_tokens=300, num_return_sequences = 1)
    return response

# prompt functions
def make_prompt(prompt_form, name, clean = False):
    #  if re.search(r'\((.*?)\)',name):
    #      inside_text = re.search(r'\((.*?)\)',name).group(1)
    #      name = "{}, {},".format(name,inside_text)
     if clean:
          name = re.sub(r'\([^)]*\)', '', name)
     return prompt_form.format(name)

def remove_prompt_from_response(prompt, response):
    len_prompt = len(prompt.split())
    if response.split()[:len_prompt] == prompt.split():
        response =  " ".join(response.split()[len_prompt:])
    return response

def strip_repsonse(text):
    text = re.sub("<pad> ","",text)
    text = re.sub("</s>","",text)
    return text


# data function
#@jit(target_backend='cuda',nopython=True)  
def prep_random_sample(data_path,wiki_wiki,size,percent=False):
    #random_keys = fh.read_json_random_sample(data_path,size=.2,percent=True,return_keys= True)
    count = 0
    random_sample_dict = {}
    with codecs.open(data_path) as input_file:
        all_data = json.load(input_file)
        if percent: 
            nsamples = int(size * len(all_data))
        else: 
            nsamples = size
        keys = random.sample(list(all_data), nsamples)
        for k in keys:
            if count %100 == 0:
                print(count)
            count +=1
            if not 'page_views' in all_data[k].keys():
                item_page = wiki_wiki.page(k)
                page_views = wf.get_page_views(item_page)
                all_data[k]['page_views'] = page_views

            random_sample_dict.update({k:all_data[k]})
        fh.write_to_json(all_data,data_path)
        return keys, random_sample_dict

# prediction 
def predict_birth_year(data, model, tokenizer, prompt_form):
    df_dict = {'Name':[],'True birth year': [], 'Pageviews':[],'Predicted birth year':[], "Years off": [], "Full response": []}
    count = 0
    for name in data.keys():
        true_birth_year = data[name]['birth_year']
        page_views = data[name]['page_views']

        prompt = make_prompt(prompt_form, name, clean=True)
        #response = flant5_text_to_text(prompt,model,tokenizer)
        response = gpt2_text_to_text(prompt,model,tokenizer,contrastive=True)
        response = remove_prompt_from_response(prompt,response)
        if count < 10:
            print(prompt)
            print(response)
        count += 1
        prediction_year = re.findall("\d{4}",response)
        if prediction_year:
            response_year = int(prediction_year[0])
            difference = abs(true_birth_year-response_year)
            
        else: 
            response_year = "no prediction"
            difference = "n/a"
        df_dict['Name'].append(name)
        df_dict['True birth year'].append(true_birth_year)
        df_dict['Pageviews'].append(page_views)
        df_dict['Predicted birth year'].append(response_year)
        df_dict['Years off'].append(difference)
        df_dict['Full response'].append(response)
    return df_dict

# organization 
def record_seen_keys(keys, outfile):
    if os.path.exists(outfile):
        seen_keys = fh.unpickle_data(outfile)
        fh.pickle_data(seen_keys.union(set(keys)),outfile)
    else:
        fh.pickle_data(set(keys),outfile)

def begin_log(log_base,model_string,sample_size,prompt_form, other=None):
    date = '{}'.format( datetime.datetime.now().strftime('%Y-%m-%d-%H-%M') )
    suffix = "{}_{}_{}".format(model_string,sample_size, date)
    result_path = os.path.join(log_base, suffix)
    os.mkdir(result_path)

    # log parameters 
    log_file_name = "{}_{}samp_log.csv".format(model_string,sample_size)
    log_file_path = os.path.join(result_path,log_file_name)
    f = open(log_file_path,"w")
    f.write("model:{}\n".format(model_string))
    f.write("sample size: {}\n".format(sample_size))
    f.write("prompt form: {}\n".format(prompt_form))
    if other:
        f.write("other: {}".format(other))

    return result_path



def main(): # parameters are: data_path, size, model + model parameters, prompt_form, outpath, csv outpath, seed 
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--data_path',default="/data/madesai/history-llm-data/wikipedia-json-files/all_wiki.json")
    # parser.add_argument('--new_sample',default=True)
    # parser.add_argument('--sample_size')

    
    data_path = "/data/madesai/history-llm-data/wikipedia-json-files/all_wiki.json"
   # log_base = "/data/madesai/history-llm-data/logs/predict_birth_year/"
    log_base = "/home/madesai/generate-text/predict-birthyear/log/"
   # prompt_form = "What year was {} born?"
    prompt_form = "{} was born in the year"
    sample = 0.005
    percent = True
    #sample = 0.001
    #percent = True

    wiki_wiki = wf.initiate_request()
   # keys, data = prep_random_sample(data_path,wiki_wiki,size=sample,percent=percent)
   # keys_out = "/data/madesai/history-llm-data/experiment_keys.pkl"
   # record_seen_keys(keys, keys_out)
    keys = fh.unpickle_data("/data/madesai/history-llm-data/experiment_keys.pkl")
    all_data = fh.read_json(data_path)
    data = {}
    for name in keys:
        data.update({name:all_data[name]})
    sample_size = len(keys)

    set_seed(42)
    #model, tokenizer, model_string = initiate_gpt2(large=True)
    #model,tokenizer, model_string = initiate_flan5_text_to_text(xxl=True)
    model, tokenizer, model_string = initiate_falcon(fourtyb=True)
    
    
    log_path = begin_log(log_base, model_string, sample_size, prompt_form)

    csv_out_name = "{}_{}samp.csv".format(model_string,len(keys))
    csv_out = os.path.join(log_path,csv_out_name)
    

    pred_dict = predict_birth_year(data,model,tokenizer,prompt_form)
    df = pd.DataFrame(pred_dict)
    df.to_csv(csv_out,sep=";")

if __name__ == "__main__":
    main()
    # model, tokenizer, model_string = initiate_falcon()
    # prompt = "Paris Hilton was born in the year"
    # response = gpt2_text_to_text(prompt,model,tokenizer,contrastive=True)
    # print(response)