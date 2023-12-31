from string import punctuation
# removes duplicates and formats list questions 

path_to_questions = "/home/madesai/generate-text/get-textbook-questions/"
qf = "Glencoe-US-section-questions-clean.txt"
outfile = open(qf[:-4]+"-prompts.txt","w")
question_file = open(path_to_questions+qf,"r")

seen_prompts = set()
for prompt in question_file:
    check_list_prompt = prompt.split(": ")
    if check_list_prompt[0] == "Identify":
        for item in check_list_prompt[1].split(", "):
            item = item.strip().strip(punctuation)
            if item not in seen_prompts:
                prompt = "{} was ".format(item)
                outfile.write(prompt+"\n")
                seen_prompts.add(item)
            
            
            
    elif check_list_prompt[0] != "Define" and prompt not in seen_prompts:
        outfile.write(prompt)
        seen_prompts.add(prompt)
outfile.close()

        
    
    
    
